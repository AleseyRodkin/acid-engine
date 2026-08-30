use std::io::{self, Read};
use std::process::ExitCode;

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
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("ERROR: {e}");
            ExitCode::from(2)
        }
    }
}
