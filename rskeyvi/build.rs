extern crate bindgen;
extern crate cmake;

use std::env;
use std::path::PathBuf;

fn main() {
    let dst = cmake::build("../");

    // Tell cargo to tell rustc to link keyvi
    println!("cargo:rustc-link-lib=dylib=keyvirust");
    println!("cargo:rustc-link-search=native={}", dst.join("build").display());

    // The bindgen::Builder is the main entry point
    // to bindgen, and lets you build up options for
    // the resulting bindings.
    println!("Starting to generate bindings..");

    let bindings = bindgen::Builder::default()
        // The input header we would like to generate
        // bindings for.
        .header("wrapper.h")
        .clang_arg("-I../keyvi/src/cpp/")
        .clang_arg("-x").clang_arg("c++")
        .clang_arg("-std=c++11")
        .enable_cxx_namespaces()

        .layout_tests(true)
        // Finish the builder and generate the bindings.
        .generate()
        // Unwrap the Result and panic on failure.
        .expect("Unable to generate bindings");

    println!("Saving to bindings..");
    // Write the bindings to the $OUT_DIR/bindings.rs file.
    let out_path = PathBuf::from(env::var("OUT_DIR").unwrap());
    bindings
        .write_to_file(out_path.join("bindings.rs"))
        .expect("Couldn't write bindings!");
}

