from setuptools import setup, Extension
import distutils.command.build as _build
import distutils.command.bdist_rpm as _bdist_rpm
import distutils.command.build_ext as _build_ext
import os
import sys
import tempfile
import subprocess
import multiprocessing

from contextlib import contextmanager
from os import path


@contextmanager
def symlink_keyvi():
    if not path.exists('keyvi'):
        os.symlink('../keyvi', 'keyvi')
        yield
        os.unlink('keyvi')
    else:
        yield


with symlink_keyvi() as _:
    # workaround for autwrap bug (includes incompatible boost)
    autowrap_data_dir = "autowrap_includes"

    dictionary_sources = path.abspath('keyvi')
    tpie_build_dir = path.join(dictionary_sources, '3rdparty/tpie/build')
    tpie_install_prefix = 'install'
    tpie_include_dir = path.join(tpie_build_dir, tpie_install_prefix, 'include')
    tpie_lib_dir = path.join(tpie_build_dir, tpie_install_prefix, 'lib')

    additional_compile_flags = []

    linklibraries_static_or_dynamic = [
        "boost_program_options",
        "boost_iostreams",
        "boost_filesystem",
        "boost_system",
        "boost_regex",
        "boost_thread",
        "snappy"
    ]

    linklibraries = [
        "tpie",
        "z"
    ]

    extra_link_arguments = []

    if sys.platform == 'darwin':
        additional_compile_flags.append("-DOS_MACOSX")
        linklibraries_static_or_dynamic.remove('boost_thread')
        linklibraries_static_or_dynamic.append('boost_thread-mt')

    #########################
    # Custom 'build' command
    #########################

    custom_user_options = [('mode=',
                            None,
                            "build mode."),
                           ('staticlinkboost',
                            None,
                            "special mode to statically link boost."),
                           ]


    class custom_opts:

        parent = None

        def initialize_options(self):
            self.parent.initialize_options(self)
            self.mode = 'release'
            self.staticlinkboost = False

        def run(self):
            global additional_compile_flags
            global linklibraries
            global linklibraries_static_or_dynamic
            global extra_link_arguments
            global ext_modules
            print "Building in {} mode".format(self.mode)

            if self.mode == 'debug':
                additional_compile_flags.append("-O0")
                additional_compile_flags.append("-ggdb3")
                additional_compile_flags.append("-fstack-protector")
            else:
                additional_compile_flags.append("-O3")

            if self.mode == 'coverage':
                additional_compile_flags.append("--coverage")
                linklibraries.append("gcov")

            # check linking
            if self.staticlinkboost:
                # set static
                extra_link_arguments = ['-Wl,-Bstatic']
                for lib in linklibraries_static_or_dynamic:
                    extra_link_arguments.append("-l{}".format(lib))
                # reset to dynamic
                extra_link_arguments.append('-Wl,-Bdynamic')
                extra_link_arguments.append('-static-libstdc++')
                extra_link_arguments.append('-static-libgcc')
                # workaround: link librt explicitly
                linklibraries.append("rt")
            else:
                # no static linking, add the libs to dynamic linker
                linklibraries += linklibraries_static_or_dynamic

            # patch the compile flags
            for ext_m in ext_modules:
                flags = getattr(ext_m, 'extra_compile_args') + additional_compile_flags
                setattr(ext_m, 'extra_compile_args', flags)
                setattr(ext_m, 'libraries', linklibraries)
                args = getattr(ext_m, 'extra_link_args') + extra_link_arguments
                setattr(ext_m, 'extra_link_args', args)

            self.parent.run(self)


    class build(custom_opts, _build.build):
        parent = _build.build
        user_options = _build.build.user_options + custom_user_options


    class build_ext(_build_ext.build_ext):
        def run(self):
            if not path.exists(path.join(tpie_lib_dir, 'libtpie.a')):
                try:
                    cpu_count = multiprocessing.cpu_count()
                except:
                    cpu_count = 1

                tpie_build_cmd = 'mkdir -p {}'.format(tpie_build_dir)
                tpie_build_cmd += ' && cd {}'.format(tpie_build_dir)
                tpie_build_cmd += ' && cmake -D CMAKE_BUILD_TYPE:STRING=Release ' \
                                  ' -D TPIE_PARALLEL_SORT=1 -D CMAKE_CXX_FLAGS="-fPIC -std=c++11"' \
                                  ' -D CMAKE_INSTALL_PREFIX={} ..'.format(tpie_install_prefix)
                tpie_build_cmd += ' && make -j {}'.format(cpu_count)
                tpie_build_cmd += ' && make install'

                subprocess.call(tpie_build_cmd, shell=True)

            os.environ['ARCHFLAGS'] = '-arch x86_64'
            _build_ext.build_ext.run(self)


    class bdist_rpm(custom_opts, _bdist_rpm.bdist_rpm):
        parent = _bdist_rpm.bdist_rpm
        user_options = _bdist_rpm.bdist_rpm.user_options + custom_user_options

        def run(self):
            def_setup_call = "%s %s build" % (self.python, os.path.basename(sys.argv[0]))

            if self.staticlinkboost:
                def_setup_call += " --staticlinkboost"

            def_setup_call += " --mode " + self.mode
            with tempfile.NamedTemporaryFile(suffix="_pykeyvi_rpm") as tmp:
                # Do stuff with tmp
                tmp.write(def_setup_call)
                tmp.flush()
                self.build_script = tmp.name

                self.parent.run(self)


    ext_modules = [Extension('pykeyvi',
                             include_dirs=[autowrap_data_dir,
                                           tpie_include_dir,
                                           os.path.join(dictionary_sources, 'src/cpp'),
                                           os.path.join(dictionary_sources, '3rdparty/rapidjson/include'),
                                           os.path.join(dictionary_sources, '3rdparty/msgpack-c/include'),
                                           os.path.join(dictionary_sources, '3rdparty/utf8'),
                                           os.path.join(dictionary_sources, '3rdparty/misc'),
                                           os.path.join(dictionary_sources, '3rdparty/xchange/src')],
                             language='c++',
                             sources=['src/pykeyvi.cpp'],
                             extra_compile_args=['-std=c++11', '-msse4.2'] + additional_compile_flags,
                             extra_link_args=[],
                             library_dirs=[tpie_lib_dir],
                             libraries=linklibraries)]

    PACKAGE_NAME = 'python-keyvi'

    install_requires = [
        'msgpack-python',
    ]

    setup(
        name=PACKAGE_NAME,
        version='0.1.19',
        description='Python bindings for keyvi',
        author='Hendrik Muhs',
        author_email='hendrik.muhs@gmail.com',
        license="ASL 2.0",
        cmdclass={'build_ext': build_ext, 'build': build, 'bdist_rpm': bdist_rpm},
        ext_modules=ext_modules,
        zip_safe=False,
        url='https://github.com/cliqz/keyvi',
        download_url='https://github.com/cliqz/keyvi/tarball/v0.1.19',
        keywords=['FST'],
        classifiers=[],
        install_requires=install_requires,
    )
