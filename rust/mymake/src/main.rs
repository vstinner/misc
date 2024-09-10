use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};

fn main() {
    let child = Command::new("make")  // FIXME: pass argv[1:] to make
        .stdout(Stdio::piped())
        .spawn().unwrap();
    let stdout = child.stdout.unwrap();
    let reader = BufReader::new(stdout);
    // FIXME: exitcode

    let mut warnings = Vec::new();
    let mut errors = Vec::new();
    for line in reader.lines() {
        let line = line.unwrap();
        println!("{}", line);
        if line.starts_with("warning: ") {
            // FIXME: strip line
            warnings.push(line);
        }
        else if line.starts_with("error: ") {
            // FIXME: strip line
            errors.push(line);
        }
    }

    if warnings.len() > 0 {
        println!();
        for line in &warnings {
            println!("WARNING: {}", line);
        }
    }
    if errors.len() > 0 {
        println!();
        for line in &errors {
            println!("ERROR: {}", line);
        }
    }

    println!();
    if warnings.len() > 0 || errors.len() > 0 {
        println!("Build OK but with some warnings/errors");
    }
    else {
        println!("Build OK: no compiler warnings or errors");
    }
}
