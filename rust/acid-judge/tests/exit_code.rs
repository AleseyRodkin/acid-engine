//! Binary exit: 0 PASS, 1 FAIL, 2 input error or SKIPPED. JSON body is unchanged.
use std::io::Write;
use std::process::{Command, Stdio};

fn run(input: &str) -> (i32, String, String) {
    let mut child = Command::new(env!("CARGO_BIN_EXE_acid-judge"))
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("spawn acid-judge");
    child
        .stdin
        .as_mut()
        .expect("stdin")
        .write_all(input.as_bytes())
        .expect("write stdin");
    let out = child.wait_with_output().expect("wait");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

#[test]
fn empty_json_is_skipped_exit_two() {
    let (code, stdout, _) = run("{}");
    assert_eq!(code, 2, "stdout={stdout}");
    assert!(stdout.contains("SKIPPED"), "stdout={stdout}");
    assert!(!stdout.contains("\"status\":\"PASS\""));
}

#[test]
fn empty_worker_script_is_fail_exit_one() {
    let (code, stdout, _) = run(r#"{"worker":{"script":""}}"#);
    assert_eq!(code, 1, "stdout={stdout}");
    assert!(stdout.contains("FAIL"), "stdout={stdout}");
}

#[test]
fn invalid_json_is_exit_two() {
    let (code, _, stderr) = run("not-json");
    assert_eq!(code, 2);
    assert!(stderr.contains("invalid json") || stderr.contains("ERROR"));
}
