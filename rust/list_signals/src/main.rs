use libc::{strsignal as _strsignal, c_char};
use std::ffi::CStr;
use std::str;

fn strsignal(signum: i32) -> String {
    let c_buf: *const c_char = unsafe { _strsignal(signum) };
    let c_str: &CStr = unsafe { CStr::from_ptr(c_buf) };
    let str_slice: &str = c_str.to_str().unwrap();
    let str_buf: String = str_slice.to_owned();
    str_buf
}

fn main() {
    for signum in 0..256 {
        let signame = strsignal(signum);
        if signame.starts_with("Unknown signal ") {
            continue;
        }
        println!("signal {}: {}", signum, signame);
    }
}
