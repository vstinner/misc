Articles
========

* nbody: C vers Rust
  http://cliffle.com/p/dangerust/1/
* https://doc.rust-lang.org/nightly/nomicon/intro.html
* Learn Rust With Entirely Too Many Linked Lists
  https://rust-unofficial.github.io/too-many-lists/index.html

typeof
======

fn print_type_of<T>(_: &T) {
    println!("{}", std::any::type_name::<T>())
}

print_type_of(&var);
