use std::process::{Command, Stdio, ChildStdout};
use std::io::{BufRead, BufReader, Lines};
use std::time::Instant;
use std::env;

enum MatchType {
    WARNING,
    ERROR
}

fn parse_output(lines: Lines<BufReader<ChildStdout>>, matched: &mut Vec<(MatchType, String)>) {
    for line in lines {
        let line = line.unwrap();
        println!("{}", line);

        if line.starts_with("warning: ") {
            matched.push((MatchType::WARNING, line));
        }
        else if line.starts_with("error: ") {
            matched.push((MatchType::ERROR, line));
        }
    }
}

fn main() {
    let start_time = Instant::now();

    let mut child = Command::new("make")
        .args(env::args())
        .stdout(Stdio::piped())
        //.stderr(Stdio::piped())
        .spawn().unwrap();

    let mut matched = Vec::new();

    let stdout = child.stdout.take().unwrap();
    let reader = BufReader::new(stdout);
    parse_output(reader.lines(), &mut matched);

    // let stderr = child.stderr.take().unwrap();
    // let reader = BufReader::new(stderr);
    // parse_output(reader.lines(), &mut matched);

    let exitcode = child.wait().expect("process complete");
    let exitcode = exitcode.code().unwrap();
    let duration = start_time.elapsed();
    let duration = (duration.as_millis() as f64) / 1e3;
    let duration = format!("{duration} sec");

    if matched.len() > 0 {
        println!();
        let mut warnings = 0;
        let mut errors = 0;
        if matched.len() > 0 {
            for line in &matched {
                println!("{}", line.1);
                match line.0 {
                    MatchType::WARNING => warnings += 1,
                    MatchType::ERROR => errors += 1,
                }
            }
        }
        println!("=> Found {} warnings and {} errors", warnings, errors);
    }

    println!();
    if exitcode != 0 {
        println!("Build FAILED with exit code {} ({})", exitcode, duration);
    }
    else if matched.len() > 0 {
        println!("Build OK but with some warnings/errors ({})", duration);
    }
    else {
        println!("Build OK: no compiler warnings or errors ({})", duration);
    }
}
