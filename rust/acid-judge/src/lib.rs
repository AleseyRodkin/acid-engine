//! Supervisor: bind plan.lock, run a Python worker, then verdict.
//! Body hash is Python canon only. Without `worker` the binary does not judge: SKIPPED, not PASS.
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::path::Path;
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
    let ident = match spawn_worker(worker, "identify", None) {
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
    let ran = match spawn_worker(worker, "run", worker.input.clone()) {
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
    worker: &WorkerSpec,
    op: &str,
    input: Option<Value>,
) -> Result<WorkerOut, String> {
    let python = worker.python.as_deref().unwrap_or("python3");
    let cwd = worker.cwd.as_deref().unwrap_or(".");
    let mut payload = serde_json::Map::new();
    payload.insert("op".into(), Value::String(op.into()));
    payload.insert("script".into(), Value::String(worker.script.clone()));
    if op == "run" {
        payload.insert("input".into(), input.unwrap_or(Value::Null));
    }
    let body = Value::Object(payload);
    let mut pythonpath = cwd.to_string();
    if let Ok(existing) = std::env::var("PYTHONPATH") {
        if !existing.is_empty() {
            pythonpath = format!("{pythonpath}:{existing}");
        }
    }
    let mut child = Command::new(python)
        .arg("-m")
        .arg("acid_engine.worker")
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
    let cwd = worker.cwd.as_deref().unwrap_or(".");
    let path = Path::new(cwd).join("acid_engine").join("worker.py");
    match sha256_file(&path) {
        Ok(actual) if actual == expected => None,
        Ok(_) => Some(Response::fail("worker source hash mismatch", "worker_hash")),
        Err(e) => Some(Response::fail(e, "worker_hash")),
    }
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
    let required = req.output_type.as_deref().unwrap_or("");
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

fn type_matches(required: &str, value: &Value) -> bool {
    match required {
        "int" => matches!(value, Value::Number(n) if n.as_i64().is_some() || n.as_u64().is_some()),
        "bool" => value.is_boolean(),
        "float" => matches!(value, Value::Number(_)),
        "str" => value.is_string(),
        "list" => value.is_array(),
        "dict" | "record" => value.is_object(),
        "None" => value.is_null(),
        "" => true,
        _ => true,
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
        let tmp = std::env::temp_dir().join(format!("acid-worker-pin-{}", std::process::id()));
        let pkg = tmp.join("acid_engine");
        std::fs::create_dir_all(&pkg).unwrap();
        std::fs::write(pkg.join("worker.py"), b"print('tamper')\n").unwrap();
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
}
