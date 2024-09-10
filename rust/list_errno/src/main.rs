use core::str;
use libc::{strerror_r, size_t, strlen};

fn from_utf8_lossy(input: &[u8]) -> &str {
    match str::from_utf8(input) {
        Ok(valid) => valid,
        Err(error) => unsafe { str::from_utf8_unchecked(&input[..error.valid_up_to()]) },
    }
}

fn strerror(errno: i32) -> Option<String> {
    let mut buf = [0u8; 1024];
    let c_str = unsafe {
        let rc = strerror_r(errno, buf.as_mut_ptr() as *mut _, buf.len() as size_t);
        if rc != 0 {
            return None;
        }
        let c_str_len = strlen(buf.as_ptr() as *const _);
        &buf[..c_str_len]
    };
    let err_msg = from_utf8_lossy(c_str);
    return Some(String::from(err_msg));
}

fn main() {
    for errno in 0..256 {
        let err_msg = strerror(errno);
        match err_msg {
            None => (),
            Some(err_msg_str) => println!("{}: {}", errno, err_msg_str),
        }
    }
}
