use std::io::{self, Read};
use std::process::ExitCode;

fn exit_status(status: &str) -> u8 {
    match status {
        "PASS" => 0,
        "FAIL" => 1,
        _ => 2,
    }
}

fn main() -> ExitCode {
    let mut raw = String::new();
    if let Err(e) = io::stdin().read_to_string(&mut raw) {
        eprintln!("ERROR: {e}");
        return ExitCode::from(2);
    }
    let req: acid_judge::Request = match serde_json::from_str(raw.trim()) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("ERROR: invalid json: {e}");
            return ExitCode::from(2);
        }
    };
    let out = acid_judge::judge(&req);
    match serde_json::to_string(&out) {
        Ok(s) => {
            println!("{s}");
            ExitCode::from(exit_status(&out.status))
        }
        Err(e) => {
            eprintln!("ERROR: {e}");
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::exit_status;

    #[test]
    fn pass_is_zero() {
        assert_eq!(exit_status("PASS"), 0);
    }

    #[test]
    fn fail_is_one() {
        assert_eq!(exit_status("FAIL"), 1);
    }

    #[test]
    fn no_worker_skipped_is_two() {
        assert_eq!(exit_status("SKIPPED"), 2);
    }
}
