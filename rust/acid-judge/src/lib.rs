//! Supervisor: bind plan.lock, run a Python worker, then verdict.
//! Body hash is Python canon only. Without `worker` the binary does not judge: SKIPPED, not PASS.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Observation {
    #[serde(default)]
    pub status: String,
    #[serde(default)]
    pub latency_ms: Option<f64>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct WorkerSpec {
    #[serde(default)]
    pub python: Option<String>,
    #[serde(default)]
    pub script: String,
    #[serde(default)]
    pub input: Option<Value>,
    #[serde(default)]
    pub cwd: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Request {
    #[serde(default)]
    pub module_hashes: BTreeMap<String, String>,
    pub script_name: Option<String>,
    pub script_hash: Option<String>,
    pub contract_id: Option<String>,
    pub observation: Option<Observation>,
    pub output_type: Option<String>,
    pub data: Option<Value>,
    #[serde(default)]
    pub pure: bool,
    #[serde(default)]
    pub effects: Vec<String>,
    #[serde(default)]
    pub worker: Option<WorkerSpec>,
    #[serde(default)]
    pub worker_hash: Option<String>,
    #[serde(default)]
    pub runtime_hashes: BTreeMap<String, String>,
    #[serde(default)]
    pub source_hash: Option<String>,
    #[serde(default)]
    pub dependency_hashes: BTreeMap<String, String>,
    #[serde(default)]
    pub max_latency_ms: Option<f64>,
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Response {
    pub status: String,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub property: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<Value>,
}

impl Response {
    fn skipped(message: impl Into<String>) -> Self {
        Self {
            status: "SKIPPED".into(),
            message: message.into(),
            property: None,
            data: None,
        }
    }
    fn fail(message: impl Into<String>, property: &str) -> Self {
        Self {
            status: "FAIL".into(),
            message: message.into(),
            property: Some(property.into()),
            data: None,
        }
    }
    fn pass(message: impl Into<String>) -> Self {
        Self {
            status: "PASS".into(),
            message: message.into(),
            property: None,
            data: None,
        }
    }
}

#[derive(Debug, Clone, Deserialize, Default)]
struct WorkerOut {
    #[serde(default)]
    script_name: Option<String>,
    #[serde(default)]
    script_hash: String,
    #[serde(default)]
    contract_id: Option<String>,
    #[serde(default)]
    output_type: Option<String>,
    #[serde(default)]
    pure: bool,
    #[serde(default)]
    max_latency_ms: Option<f64>,
    #[serde(default)]
    data: Option<Value>,
    #[serde(default)]
    effects: Vec<String>,
    #[serde(default)]
    observation: Option<Observation>,
}

pub fn judge(req: &Request) -> Response {
    if let Some(worker) = req.worker.as_ref() {
        return judge_with_worker(req, worker);
    }
    Response::skipped("no worker: observation-only is not a verdict")
}

fn judge_with_worker(req: &Request, worker: &WorkerSpec) -> Response {
    if worker.script.trim().is_empty() {
        return Response::fail("worker.script is empty", "worker");
    }
    if let Some(pin) = pin_worker(req, worker) {
        return pin;
    }
    if let Some(pin) = pin_runtime(req, worker) {
        return pin;
    }
    let source_hash = match req.source_hash.as_deref() {
        Some(h) if !h.is_empty() => h,
        _ => return Response::skipped("source not pinned"),
    };
    let ident = match spawn_worker(req, worker, "identify", None, Some(source_hash)) {
        Ok(v) => v,
        Err(e) => return Response::fail(e, "worker"),
    };
    if ident.script_hash.is_empty() {
        return Response::fail("worker identify returned no script_hash", "worker");
    }
    if let Some(claimed) = req.script_hash.as_deref() {
        if !claimed.is_empty() && claimed != ident.script_hash {
            return Response::fail(
                "worker identity hash != request script_hash",
                "script_hash",
            );
        }
    }
    let mut bound_req = req.clone();
    bound_req.script_hash = Some(ident.script_hash.clone());
    bound_req.script_name = ident
        .script_name
        .clone()
        .or(bound_req.script_name.clone());
    bound_req.contract_id = ident
        .contract_id
        .clone()
        .or(bound_req.contract_id.clone());
    bound_req.pure = ident.pure;
    bound_req.max_latency_ms = ident.max_latency_ms.or(bound_req.max_latency_ms);
    if bound_req.output_type.is_none() {
        bound_req.output_type = ident.output_type.clone();
    }
    let bound = bind(&bound_req);
    if bound.status != "BOUND" {
        return bound;
    }
    let ran = match spawn_worker(req, worker, "run", worker.input.clone(), Some(source_hash)) {
        Ok(v) => v,
        Err(e) => return Response::fail(e, "worker"),
    };
    if ran.script_hash != ident.script_hash {
        return Response::fail("worker run hash != identify hash", "script_hash");
    }
    let Some(obs) = ran.observation.clone() else {
        return Response::skipped("bound but worker returned no observation");
    };
    bound_req.data = ran.data.clone();
    bound_req.effects = ran.effects.clone();
    if let Some(t) = ran.output_type.clone().or(ident.output_type.clone()) {
        bound_req.output_type = Some(t);
    }
    let mut resp = verdict(&bound_req, &obs);
    if resp.status == "PASS" {
        resp.data = ran.data;
    }
    resp
}

fn spawn_worker(
    req: &Request,
    worker: &WorkerSpec,
    op: &str,
    input: Option<Value>,
    source_hash: Option<&str>,
) -> Result<WorkerOut, String> {
    let python = worker.python.as_deref().unwrap_or("python3");
    let cwd = worker.cwd.as_deref().unwrap_or(".");
    let root = engine_root(worker)?;
    let worker_py = root.join("acid_engine").join("worker.py");
    if !worker_py.is_file() {
        return Err(format!("worker source missing: {}", worker_py.display()));
    }
    let mut payload = serde_json::Map::new();
    payload.insert("op".into(), Value::String(op.into()));
    payload.insert("script".into(), Value::String(worker.script.clone()));
    if op == "run" {
        payload.insert("input".into(), input.unwrap_or(Value::Null));
    }
    if let Some(h) = source_hash {
        payload.insert("source_hash".into(), Value::String(h.into()));
    }
    payload.insert(
        "module_hashes".into(),
        serde_json::to_value(&req.module_hashes).unwrap_or(Value::Null),
    );
    payload.insert(
        "dependency_hashes".into(),
        serde_json::to_value(&req.dependency_hashes).unwrap_or(Value::Null),
    );
    let body = Value::Object(payload);
    let mut path_parts: Vec<PathBuf> = vec![root];
    if let Some(existing) = std::env::var_os("PYTHONPATH") {
        path_parts.extend(std::env::split_paths(&existing));
    }
    let pythonpath = std::env::join_paths(&path_parts).unwrap_or_else(|_| cwd.into());
    let mut child = Command::new(python)
        .arg(&worker_py)
        .current_dir(cwd)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYTHONPATH", pythonpath)
        .spawn()
        .map_err(|e| format!("spawn worker: {e}"))?;
    {
        let stdin = child
            .stdin
            .as_mut()
            .ok_or_else(|| "worker stdin closed".to_string())?;
        stdin
            .write_all(body.to_string().as_bytes())
            .map_err(|e| format!("write worker: {e}"))?;
    }
    let out = child
        .wait_with_output()
        .map_err(|e| format!("wait worker: {e}"))?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(format!(
            "worker exit {}: {}",
            out.status.code().unwrap_or(-1),
            err.trim()
        ));
    }
    let text = String::from_utf8_lossy(&out.stdout);
    serde_json::from_str(text.trim()).map_err(|e| format!("worker json: {e}"))
}

fn pin_worker(req: &Request, worker: &WorkerSpec) -> Option<Response> {
    let expected = match req.worker_hash.as_deref() {
        Some(h) if !h.is_empty() => h.to_lowercase(),
        _ => return Some(Response::skipped("worker not pinned")),
    };
    let root = match engine_root(worker) {
        Ok(p) => p,
        Err(e) => return Some(Response::fail(e, "worker_hash")),
    };
    let path = root.join("acid_engine").join("worker.py");
    match sha256_file(&path) {
        Ok(actual) if actual == expected => None,
        Ok(_) => Some(Response::fail("worker source hash mismatch", "worker_hash")),
        Err(e) => Some(Response::fail(e, "worker_hash")),
    }
}

const RUNTIME_PIN_PATHS: &[&str] = &[
    "acid_engine/worker.py",
    "acid_engine/level3/script/python_runtime.py",
    "acid_engine/level3/script/runner.py",
    "acid_engine/level3/script/resolve.py",
    "acid_engine/level2/implementation_canon.py",
    "acid_engine/level2/local_deps.py",
    "acid_engine/cli_judge.py",
    "acid_engine/action_driver.py",
];

fn pin_rel_ok(rel: &str) -> bool {
    !rel.contains("..")
        && !rel.contains('\0')
        && rel.starts_with("acid_engine/")
        && rel.ends_with(".py")
}

fn pin_runtime(req: &Request, worker: &WorkerSpec) -> Option<Response> {
    if req.runtime_hashes.is_empty() {
        return Some(Response::skipped("runtime not pinned"));
    }
    for rel in RUNTIME_PIN_PATHS {
        if !req.runtime_hashes.contains_key(*rel) {
            return Some(Response::skipped("runtime not pinned"));
        }
    }
    let root = match engine_root(worker) {
        Ok(p) => p,
        Err(e) => return Some(Response::fail(e, "runtime_hash")),
    };
    for (rel, want) in &req.runtime_hashes {
        if !pin_rel_ok(rel) {
            return Some(Response::fail("runtime path rejected", "runtime_hash"));
        }
        let path = root.join(rel);
        let expected = want.to_lowercase();
        match sha256_file(&path) {
            Ok(actual) if actual == expected => {}
            Ok(_) => {
                return Some(Response::fail(
                    format!("runtime source hash mismatch: {rel}"),
                    "runtime_hash",
                ))
            }
            Err(e) => return Some(Response::fail(e, "runtime_hash")),
        }
    }
    None
}

fn engine_root(worker: &WorkerSpec) -> Result<PathBuf, String> {
    if let Ok(raw) = std::env::var("ACID_ENGINE_ROOT") {
        if !raw.trim().is_empty() {
            return resolve_root_dir(Path::new(&raw))
                .map_err(|e| format!("ACID_ENGINE_ROOT: {e}"));
        }
    }
    let cwd = worker.cwd.as_deref().unwrap_or(".");
    locate_via_python(worker).or_else(|_| {
        if Path::new(cwd).join("acid_engine").join("worker.py").is_file() {
            Ok(Path::new(cwd).to_path_buf())
        } else {
            Err("acid_engine package not found".into())
        }
    })
}

fn resolve_root_dir(p: &Path) -> Result<PathBuf, String> {
    if p.join("acid_engine").join("worker.py").is_file() {
        return Ok(p.to_path_buf());
    }
    if p.join("worker.py").is_file()
        && p.file_name().and_then(|n| n.to_str()) == Some("acid_engine")
    {
        if let Some(parent) = p.parent() {
            return Ok(parent.to_path_buf());
        }
    }
    Err(format!(
        "worker source missing: {}",
        p.join("acid_engine").join("worker.py").display()
    ))
}

fn locate_via_python(worker: &WorkerSpec) -> Result<PathBuf, String> {
    let python = worker.python.as_deref().unwrap_or("python3");
    let out = Command::new(python)
        .arg("-P")
        .args([
            "-c",
            "import acid_engine, pathlib; print(pathlib.Path(acid_engine.__file__).resolve().parent.parent)",
        ])
        .env_remove("PYTHONPATH")
        .output()
        .map_err(|e| format!("locate acid_engine: {e}"))?;
    if !out.status.success() {
        let err = String::from_utf8_lossy(&out.stderr);
        return Err(format!(
            "acid_engine package not found (pip install the package or set ACID_ENGINE_ROOT). {}",
            err.trim()
        ));
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let root = PathBuf::from(text.trim());
    resolve_root_dir(&root)
}

fn sha256_file(path: &Path) -> Result<String, String> {
    if !path.is_file() {
        return Err(format!("worker source missing: {}", path.display()));
    }
    let attempts = [
        Command::new("sha256sum").arg(path).output(),
        Command::new("shasum").args(["-a", "256"]).arg(path).output(),
        Command::new("openssl")
            .args(["dgst", "-sha256", "-r"])
            .arg(path)
            .output(),
    ];
    let mut last_err = "no hash tool".to_string();
    for result in attempts {
        match result {
            Ok(out) if out.status.success() => {
                let text = String::from_utf8_lossy(&out.stdout);
                if let Some(hex) = parse_sha256_output(&text) {
                    return Ok(hex);
                }
                last_err = format!("bad hash output: {text}");
            }
            Ok(out) => {
                last_err = format!(
                    "hash exit {}: {}",
                    out.status.code().unwrap_or(-1),
                    String::from_utf8_lossy(&out.stderr).trim()
                );
            }
            Err(e) => last_err = format!("hash worker: {e}"),
        }
    }
    Err(last_err)
}

fn parse_sha256_output(text: &str) -> Option<String> {
    let trimmed = text.trim();
    let token = if let Some((_, right)) = trimmed.rsplit_once('=') {
        right.trim()
    } else {
        trimmed.split_whitespace().next().unwrap_or("")
    };
    let hex = token.trim().trim_start_matches('(').to_lowercase();
    if hex.len() == 64 && hex.chars().all(|c| c.is_ascii_hexdigit()) {
        Some(hex)
    } else {
        None
    }
}

fn bind(req: &Request) -> Response {
    if req.module_hashes.is_empty() {
        return Response::skipped("plan.lock has no module_hashes; cannot bind implementation");
    }
    let actual = match req.script_hash.as_deref() {
        Some(h) if !h.is_empty() => h,
        _ => return Response::skipped("no script_hash"),
    };
    let mut keys: Vec<String> = Vec::new();
    if let Some(n) = req.script_name.as_deref() {
        if !n.is_empty() {
            keys.push(n.to_string());
        }
    }
    if let Some(c) = req.contract_id.as_deref() {
        if !c.is_empty() {
            keys.push(c.to_string());
            if let Some((_, name)) = c.rsplit_once('/') {
                keys.push(name.to_string());
            }
        }
    }
    let mut expected: Option<(&str, &str)> = None;
    for k in &keys {
        if let Some(v) = req.module_hashes.get(k) {
            expected = Some((k.as_str(), v.as_str()));
            break;
        }
    }
    let Some((_key, want)) = expected else {
        return Response::skipped("plan.lock has no module hash for script");
    };
    if want != actual {
        return Response::fail("plan.lock module hash mismatch", "module_hash");
    }
    Response {
        status: "BOUND".into(),
        message: "bound".into(),
        property: None,
        data: None,
    }
}

fn verdict(req: &Request, obs: &Observation) -> Response {
    if obs.status == "skipped" {
        return Response::skipped("execution was skipped");
    }
    if obs.status != "completed" {
        return Response::fail("execution did not complete", "status");
    }
    let required = req.output_type.as_deref().unwrap_or("").trim();
    if !type_known(required) {
        return Response::skipped("output_type not in the type dictionary");
    }
    let data = req.data.as_ref().unwrap_or(&Value::Null);
    if !type_matches(required, data) {
        return Response::fail("Output type mismatch", "output_type");
    }
    if req.pure && !req.effects.is_empty() {
        return Response::fail("pure policy violated: effects observed", "pure");
    }
    if let Some(limit) = req.max_latency_ms {
        match obs.latency_ms {
            None => return Response::skipped("no latency fact"),
            Some(ms) if ms > limit => {
                return Response::fail("Latency exceeded", "max_latency_ms")
            }
            _ => {}
        }
    }
    Response::pass("Provided satisfies Required (structural+operational)")
}

fn type_known(required: &str) -> bool {
    matches!(
        required,
        "int" | "bool" | "float" | "str" | "list" | "dict" | "record" | "None"
    )
}

fn type_matches(required: &str, value: &Value) -> bool {
    match required {
        "int" => matches!(value, Value::Number(n) if n.as_i64().is_some() || n.as_u64().is_some()),
        "bool" => value.is_boolean(),
        "float" => matches!(value, Value::Number(_)),
        "str" => value.is_string(),
        "list" => value.is_array(),
        "dict" | "record" => value.is_object(),
        "None" => value.is_null(),
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn hashes(name: &str, h: &str) -> BTreeMap<String, String> {
        let mut m = BTreeMap::new();
        m.insert(name.into(), h.into());
        m
    }

    #[test]
    fn empty_hashes_skipped() {
        let r = judge(&Request::default());
        assert_eq!(r.status, "SKIPPED");
    }

    #[test]
    fn hashes_and_completed_obs_without_worker_is_skipped() {
        let r = judge(&Request {
            module_hashes: hashes("n_plus_one", "h"),
            script_name: Some("n_plus_one".into()),
            script_hash: Some("h".into()),
            observation: Some(Observation {
                status: "completed".into(),
                ..Default::default()
            }),
            output_type: Some("dict".into()),
            data: Some(json!({"n": 4})),
            pure: true,
            effects: vec![],
            ..Default::default()
        });
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn mismatch_hash_without_worker_is_skipped_not_fail() {
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            script_name: Some("s".into()),
            script_hash: Some("bbb".into()),
            observation: Some(Observation {
                status: "completed".into(),
                ..Default::default()
            }),
            output_type: Some("int".into()),
            data: Some(json!(1)),
            ..Default::default()
        });
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "FAIL");
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn bound_without_obs_is_skipped() {
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            script_name: Some("s".into()),
            script_hash: Some("aaa".into()),
            ..Default::default()
        });
        assert_eq!(r.status, "SKIPPED");
    }

    #[test]
    fn bool_is_not_int() {
        let r = verdict(
            &Request {
                output_type: Some("int".into()),
                data: Some(json!(true)),
                ..Default::default()
            },
            &Observation {
                status: "completed".into(),
                ..Default::default()
            },
        );
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("output_type"));
    }

    #[test]
    fn unknown_output_type_is_skipped() {
        for required in ["", "widget", "any"] {
            let r = verdict(
                &Request {
                    output_type: Some(required.into()),
                    data: Some(json!(1)),
                    ..Default::default()
                },
                &Observation {
                    status: "completed".into(),
                    ..Default::default()
                },
            );
            assert_eq!(r.status, "SKIPPED", "{required}");
            assert_ne!(r.status, "PASS");
            assert!(r.message.contains("type dictionary"));
        }
    }

    #[test]
    fn failed_obs_not_pass() {
        let r = verdict(
            &Request {
                output_type: Some("int".into()),
                data: Some(json!(42)),
                ..Default::default()
            },
            &Observation {
                status: "failed".into(),
                ..Default::default()
            },
        );
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("status"));
    }

    #[test]
    fn pure_with_effects_fail() {
        let r = verdict(
            &Request {
                output_type: Some("int".into()),
                data: Some(json!(1)),
                pure: true,
                effects: vec!["fs".into()],
                ..Default::default()
            },
            &Observation {
                status: "completed".into(),
                ..Default::default()
            },
        );
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("pure"));
    }

    #[test]
    fn latency_over_limit_fail() {
        let r = verdict(
            &Request {
                output_type: Some("int".into()),
                data: Some(json!(1)),
                max_latency_ms: Some(1.0),
                ..Default::default()
            },
            &Observation {
                status: "completed".into(),
                latency_ms: Some(50.0),
            },
        );
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("max_latency_ms"));
    }

    #[test]
    fn max_latency_without_fact_is_skipped() {
        let r = verdict(
            &Request {
                output_type: Some("int".into()),
                data: Some(json!(1)),
                max_latency_ms: Some(1.0),
                ..Default::default()
            },
            &Observation {
                status: "completed".into(),
                latency_ms: None,
            },
        );
        assert_eq!(r.status, "SKIPPED");
    }

    #[test]
    fn wrong_key_skipped_not_fallback() {
        let r = bind(&Request {
            module_hashes: hashes("unrelated", "aaa"),
            script_name: Some("scale".into()),
            script_hash: Some("aaa".into()),
            ..Default::default()
        });
        assert_eq!(r.status, "SKIPPED");
    }

    #[test]
    fn empty_worker_script_fails() {
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker: Some(WorkerSpec::default()),
            ..Default::default()
        });
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("worker"));
    }

    #[test]
    fn worker_without_hash_is_skipped() {
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                ..Default::default()
            }),
            ..Default::default()
        });
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn worker_hash_mismatch_fails_before_identify() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-worker-pin-{}", std::process::id()));
        let pkg = tmp.join("acid_engine");
        std::fs::create_dir_all(&pkg).unwrap();
        std::fs::write(pkg.join("worker.py"), b"print('tamper')\n").unwrap();
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some("0".repeat(64)),
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("worker_hash"));
    }

    #[test]
    fn worker_hash_without_runtime_hashes_is_skipped() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-worker-only-{}", std::process::id()));
        let pkg = tmp.join("acid_engine");
        std::fs::create_dir_all(&pkg).unwrap();
        std::fs::write(pkg.join("worker.py"), b"print('worker')\n").unwrap();
        let hex = sha256_file(&pkg.join("worker.py")).unwrap();
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(hex),
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn missing_source_hash_is_skipped_after_runtime_pin() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-source-skip-{}", std::process::id()));
        let files = [
            "acid_engine/worker.py",
            "acid_engine/level3/script/python_runtime.py",
            "acid_engine/level3/script/runner.py",
            "acid_engine/level3/script/resolve.py",
            "acid_engine/level2/implementation_canon.py",
            "acid_engine/level2/local_deps.py",
            "acid_engine/cli_judge.py",
            "acid_engine/action_driver.py",
        ];
        for rel in files {
            let path = tmp.join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, b"print('ok')\n").unwrap();
        }
        let worker_hex = sha256_file(&tmp.join("acid_engine/worker.py")).unwrap();
        let mut runtime = BTreeMap::new();
        for rel in files {
            runtime.insert(rel.to_string(), sha256_file(&tmp.join(rel)).unwrap());
        }
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(worker_hex),
            runtime_hashes: runtime,
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "SKIPPED");
        assert!(r.message.contains("source"));
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn runtime_hash_mismatch_fails_before_identify() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-runtime-pin-{}", std::process::id()));
        let files = [
            "acid_engine/worker.py",
            "acid_engine/level3/script/python_runtime.py",
            "acid_engine/level3/script/runner.py",
            "acid_engine/level3/script/resolve.py",
            "acid_engine/level2/implementation_canon.py",
            "acid_engine/level2/local_deps.py",
            "acid_engine/cli_judge.py",
            "acid_engine/action_driver.py",
        ];
        for rel in files {
            let path = tmp.join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, b"print('ok')\n").unwrap();
        }
        let worker_hex = sha256_file(&tmp.join("acid_engine/worker.py")).unwrap();
        let mut runtime = BTreeMap::new();
        for rel in files {
            runtime.insert(rel.to_string(), sha256_file(&tmp.join(rel)).unwrap());
        }
        runtime.insert(
            "acid_engine/level3/script/python_runtime.py".into(),
            "0".repeat(64),
        );
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(worker_hex),
            runtime_hashes: runtime,
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("runtime_hash"));
    }

    #[test]
    fn missing_cli_judge_key_is_not_pinned() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-missing-cli-judge-{}", std::process::id()));
        let files = [
            "acid_engine/worker.py",
            "acid_engine/level3/script/python_runtime.py",
            "acid_engine/level3/script/runner.py",
            "acid_engine/level3/script/resolve.py",
            "acid_engine/level2/implementation_canon.py",
            "acid_engine/level2/local_deps.py",
            "acid_engine/cli_judge.py",
            "acid_engine/action_driver.py",
        ];
        for rel in files {
            let path = tmp.join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, b"print('ok')\n").unwrap();
        }
        let worker_hex = sha256_file(&tmp.join("acid_engine/worker.py")).unwrap();
        let mut runtime = BTreeMap::new();
        for rel in files {
            if rel == "acid_engine/cli_judge.py" {
                continue;
            }
            runtime.insert(rel.to_string(), sha256_file(&tmp.join(rel)).unwrap());
        }
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(worker_hex),
            runtime_hashes: runtime,
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "PASS");
    }

    #[test]
    fn missing_action_driver_key_is_not_pinned() {
        let _guard = RootGuard::acquire();
        let tmp = std::env::temp_dir().join(format!("acid-missing-driver-{}", std::process::id()));
        let files = RUNTIME_PIN_PATHS;
        for rel in files {
            let path = tmp.join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, b"print('ok')\n").unwrap();
        }
        let worker_hex = sha256_file(&tmp.join("acid_engine/worker.py")).unwrap();
        let mut runtime = BTreeMap::new();
        for rel in files {
            if *rel == "acid_engine/action_driver.py" {
                continue;
            }
            runtime.insert(rel.to_string(), sha256_file(&tmp.join(rel)).unwrap());
        }
        std::env::set_var("ACID_ENGINE_ROOT", &tmp);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(worker_hex),
            runtime_hashes: runtime,
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(tmp.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&tmp);
        assert_eq!(r.status, "SKIPPED");
        assert_ne!(r.status, "PASS");
    }

    static ENV_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());

    struct RootGuard {
        _lock: std::sync::MutexGuard<'static, ()>,
    }
    impl RootGuard {
        fn acquire() -> Self {
            Self {
                _lock: ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner()),
            }
        }
    }
    impl Drop for RootGuard {
        fn drop(&mut self) {
            std::env::remove_var("ACID_ENGINE_ROOT");
        }
    }

    #[test]
    fn pin_uses_acid_engine_root_not_cwd() {
        let _guard = RootGuard::acquire();
        let pid = std::process::id();
        let pkg_root = std::env::temp_dir().join(format!("acid-root-pkg-{pid}"));
        let empty_cwd = std::env::temp_dir().join(format!("acid-root-cwd-{pid}"));
        let files = [
            "acid_engine/worker.py",
            "acid_engine/level3/script/python_runtime.py",
            "acid_engine/level3/script/runner.py",
            "acid_engine/level3/script/resolve.py",
            "acid_engine/level2/implementation_canon.py",
            "acid_engine/level2/local_deps.py",
            "acid_engine/cli_judge.py",
            "acid_engine/action_driver.py",
        ];
        for rel in files {
            let path = pkg_root.join(rel);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(&path, b"print('ok')\n").unwrap();
        }
        std::fs::create_dir_all(&empty_cwd).unwrap();
        let worker_hex = sha256_file(&pkg_root.join("acid_engine/worker.py")).unwrap();
        let mut runtime = BTreeMap::new();
        for rel in files {
            runtime.insert(rel.to_string(), sha256_file(&pkg_root.join(rel)).unwrap());
        }
        runtime.insert(
            "acid_engine/level3/script/python_runtime.py".into(),
            "0".repeat(64),
        );
        std::env::set_var("ACID_ENGINE_ROOT", &pkg_root);
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some(worker_hex),
            runtime_hashes: runtime,
            worker: Some(WorkerSpec {
                script: "tool.py".into(),
                cwd: Some(empty_cwd.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&pkg_root);
        let _ = std::fs::remove_dir_all(&empty_cwd);
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("runtime_hash"));
    }

    #[test]
    fn missing_cwd_package_is_not_worker_source_missing_in_cwd() {
        let _guard = RootGuard::acquire();
        std::env::remove_var("ACID_ENGINE_ROOT");
        let empty_cwd = std::env::temp_dir().join(format!(
            "acid-empty-cwd-{}",
            std::process::id()
        ));
        std::fs::create_dir_all(&empty_cwd).unwrap();
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            worker_hash: Some("0".repeat(64)),
            worker: Some(WorkerSpec {
                python: Some("python3".into()),
                script: "tool.py".into(),
                cwd: Some(empty_cwd.to_string_lossy().into()),
                ..Default::default()
            }),
            ..Default::default()
        });
        let _ = std::fs::remove_dir_all(&empty_cwd);
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("worker_hash"));
        assert!(
            !r.message.contains(&empty_cwd.join("acid_engine").to_string_lossy().to_string()),
            "must not require acid_engine under the user cwd: {}",
            r.message
        );
    }
}
