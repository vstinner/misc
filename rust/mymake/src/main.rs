use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};

fn main() {
    let mut child = Command::new("make")  // FIXME: pass argv[1:] to make
        .stdout(Stdio::piped())
        .spawn().unwrap();
    let stdout = child.stdout.take().unwrap();
    let reader = BufReader::new(stdout);

    // FIXME: measure duration
    let mut matched = Vec::new();
    for line in reader.lines() {
        let line = line.unwrap();
        println!("{}", line);

        if line.starts_with("warning: ") {
            matched.push(("warning", line));
        }
        else if line.starts_with("error: ") {
            matched.push(("error", line));
        }
    }
    let exitcode = child.wait().expect("process complete");
    let exitcode = exitcode.code().unwrap();

    if matched.len() > 0 {
        println!();
        let mut warnings = 0;
        let mut errors = 0;
        if matched.len() > 0 {
            for line in &matched {
                println!("{}", line.1);
                match line.0 {
                    "warning" => warnings += 1,
                    "error" => errors += 1,
                    _ => (),
                }
            }
        }
        println!("=> Found {} warnings and {} errors", warnings, errors);
    }

    println!();
    if exitcode != 0 {
        println!("Build FAILED with exit code {}", exitcode);
    }
    else if matched.len() > 0 {
        println!("Build OK but with some warnings/errors");
    }
    else {
        println!("Build OK: no compiler warnings or errors");
    }
}
