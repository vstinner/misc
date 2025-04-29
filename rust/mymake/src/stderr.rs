fn main() {
	let (sink, source1) = nix::unistd::pipe2(nix::fcntl::OFlag::O_CLOEXEC).unwrap();
	let source2 = source1.try_clone().unwrap();
	let _child =
		std::process::Command::new("ls")
		.arg("/foo")
		.stdin(std::process::Stdio::null())
		.stdout(source1)
		.stderr(source2)
		.spawn().unwrap();
	let sink: std::fs::File = sink.into();
	let mut sink = std::io::BufReader::new(sink);
	for line in std::io::BufRead::lines(&mut sink) {
		println!("{}", line.unwrap());
	}
}

