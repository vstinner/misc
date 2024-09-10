use std::process::{Command, Stdio};
use std::io::{BufRead, BufReader};

//fn strip(input: &mut String) {
//    let len = input.trim_end_matches(&['\r', '\n'][..]).len();
//    input.truncate(len);
//}

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
        //strip(&mut line);
        println!("{}", line);

        if line.starts_with("warning: ") {
            warnings.push(line);
        }
        else if line.starts_with("error: ") {
            errors.push(line);
        }
    }

    if warnings.len() > 0 || errors.len() > 0 {
        println!();
        if warnings.len() > 0 {
            for line in &warnings {
                println!("WARNING: {}", line);
            }
        }
        if errors.len() > 0 {
            for line in &errors {
                println!("ERROR: {}", line);
            }
        }
        println!("=> Found warnings/errors");
    }

    println!();
    if warnings.len() > 0 || errors.len() > 0 {
        println!("Build OK but with some warnings/errors");
    }
    else {
        println!("Build OK: no compiler warnings or errors");
    }
}
