//! External judge: bind plan.lock, run a Python worker, then verdict.
//! Without `worker`, observation-only mirror (no execution).
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;
use std::io::Write;
use std::process::{Command, Stdio};

#[derive(Debug, Clone, Deserialize, Default)]
pub struct Observation {
    #[serde(default)]
    pub status: String,
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
    let bound = bind(req);
    if bound.status != "BOUND" {
        return bound;
    }
    match &req.observation {
        None => Response::skipped("bound but not executed"),
        Some(obs) => verdict(req, obs),
    }
}

fn judge_with_worker(req: &Request, worker: &WorkerSpec) -> Response {
    if worker.script.trim().is_empty() {
        return Response::fail("worker.script is empty", "worker");
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

pub fn bind(req: &Request) -> Response {
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
    fn mismatch_fail_not_pass() {
        let r = judge(&Request {
            module_hashes: hashes("s", "aaa"),
            script_name: Some("s".into()),
            script_hash: Some("bbb".into()),
            observation: Some(Observation {
                status: "completed".into(),
            }),
            output_type: Some("int".into()),
            data: Some(json!(1)),
            ..Default::default()
        });
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("module_hash"));
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
    fn bones_dict_pass() {
        let r = judge(&Request {
            module_hashes: hashes("n_plus_one", "h"),
            script_name: Some("n_plus_one".into()),
            script_hash: Some("h".into()),
            observation: Some(Observation {
                status: "completed".into(),
            }),
            output_type: Some("dict".into()),
            data: Some(json!({"n": 4})),
            pure: true,
            effects: vec![],
            ..Default::default()
        });
        assert_eq!(r.status, "PASS");
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
            },
        );
        assert_eq!(r.status, "FAIL");
        assert_eq!(r.property.as_deref(), Some("pure"));
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
}
