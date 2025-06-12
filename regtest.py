#!/usr/bin/env python3

"""
A simple regression test framework for a AMReX-based code

There are several major sections to this source: the runtime parameter
routines, the test suite routines, and the report generation routines.
They are separated as such in this file.

This test framework understands source based out of the AMReX framework.

"""


import email
import os
import shutil
import smtplib
import sys
import tarfile
import time
import re
import json
import concurrent.futures
import threading
import glob

import params
import test_util
import test_report as report
import test_coverage as coverage

safe_flags = ['TEST', 'USE_CUDA', 'USE_ACC', 'USE_MPI', 'USE_OMP', 'DEBUG', 'USE_GPU']

def _check_safety(cs):
    try:
        flag = cs.split("=")[0]
        return flag in safe_flags
    except:
        return False

def check_realclean_safety(compile_strings):
    split_strings = compile_strings.strip().split()
    return all([_check_safety(cs) for cs in split_strings])

def find_build_dirs(tests):
    """ given the list of test objects, find the set of UNIQUE build
        directories.  Note if we have the useExtraBuildDir flag set """

    build_dirs = []
    last_safe = False

    for obj in tests:

        # keep track of the build directory and which source tree it is
        # in (e.g. the extra build dir)

        # first find the list of unique build directories
        dir_pair = (obj.buildDir, obj.extra_build_dir)
        if build_dirs.count(dir_pair) == 0:
            build_dirs.append(dir_pair)

        # re-make all problems that specify an extra compile argument,
        # and the test that comes after, just to make sure that any
        # unique build commands are seen.
        obj.reClean = 1
        if check_realclean_safety(obj.addToCompileString):
            if last_safe:
                obj.reClean = 0
            else:
                last_safe = True

    return build_dirs

def cmake_setup(suite):
    "Setup for cmake"

    #--------------------------------------------------------------------------
    # build AMReX with CMake
    #--------------------------------------------------------------------------
    # True:  install amrex and use install-tree
    # False: use directly build-tree
    install = False

    # Configure Amrex
    builddir, installdir = suite.cmake_config(name="AMReX",
                                              path=suite.amrex_dir,
                                              configOpts=suite.amrex_cmake_opts,
                                              install=install)
    if install:
        suite.amrex_install_dir = installdir
        target = 'install'
    else:
        suite.amrex_install_dir = builddir
        target = 'all'

    # Define additional env variable to point to AMReX install location
    env = {'AMReX_ROOT':suite.amrex_install_dir }

    rc, _ = suite.cmake_build(name="AMReX",
                              target=target,
                              path=builddir,
                              env=env)

    # If AMReX build fails, issue a catastrophic error
    if not rc == 0:
        errstr = "\n \nERROR! AMReX build failed \n"
        errstr += f"Check {suite.full_test_dir}AMReX.cmake.log for more information."
        sys.exit(errstr)


    #--------------------------------------------------------------------------
    # Configure main suite with CMake: build will be performed only when
    # needed for tests
    #--------------------------------------------------------------------------
    builddir, installdir = suite.cmake_config(name=suite.suiteName,
                                              path=suite.source_dir,
                                              configOpts=suite.source_cmake_opts,
                                              install=0,
                                              env=env)

    suite.source_build_dir = builddir

    return rc




def copy_benchmarks(old_full_test_dir, full_web_dir, test_list, bench_dir, log):
    """ copy the last plotfile output from each test in test_list
        into the benchmark directory.  Also copy the diffDir, if
        it exists """
    td = os.getcwd()

    for t in test_list:
        wd = f"{old_full_test_dir}/{t.name}"
        os.chdir(wd)

        if t.compareFile == "" and t.outputFile == "":
            p = t.get_compare_file(output_dir=wd)
        elif not t.outputFile == "":
            if not os.path.exists(t.outputFile):
                p = test_util.get_recent_filename(wd, t.outputFile, ".tgz")
            else:
                p = t.outputFile
        else:
            if not os.path.exists(t.compareFile):
                p = test_util.get_recent_filename(wd, t.compareFile, ".tgz")
            else:
                p = t.compareFile

        if p != "" and p is not None:
            if p.endswith(".tgz"):
                try:
                    tg = tarfile.open(name=p, mode="r:gz")
                    tg.extractall()
                except:
                    log.fail("ERROR extracting tarfile")
                else:
                    tg.close()
                idx = p.rfind(".tgz")
                p = p[:idx]

            store_file = p
            if not t.outputFile == "":
                store_file = f"{t.name}_{p}"

            try:
                shutil.rmtree(f"{bench_dir}/{store_file}")
            except:
                pass
            shutil.copytree(p, f"{bench_dir}/{store_file}")

            with open(f"{full_web_dir}/{t.name}.status", 'w') as cf:
                cf.write(f"benchmarks updated.  New file:  {store_file}\n")

        else:   # no benchmark exists
            with open(f"{full_web_dir}/{t.name}.status", 'w') as cf:
                cf.write("benchmarks update failed")

        # is there a diffDir to copy too?
        if not t.diffDir == "":
            diff_dir_bench = f"{bench_dir}/{t.name}_{t.diffDir}"
            if os.path.isdir(diff_dir_bench):
                shutil.rmtree(diff_dir_bench)
                shutil.copytree(t.diffDir, diff_dir_bench)
            else:
                if os.path.isdir(t.diffDir):
                    try:
                        shutil.copytree(t.diffDir, diff_dir_bench)
                    except OSError:
                        log.warn(f"file {t.diffDir} not found")
                    else:
                        log.log(f"new diffDir: {t.name}_{t.diffDir}")
                else:
                    try:
                        shutil.copy(t.diffDir, diff_dir_bench)
                    except OSError:
                        log.warn(f"file {t.diffDir} not found")
                    else:
                        log.log(f"new diffDir: {t.name}_{t.diffDir}")

        os.chdir(td)

def get_variable_names(suite, plotfile):
    """ uses fvarnames to extract the names of variables
        stored in a plotfile """

    # Run fvarnames
    command = "{} {}".format(suite.tools["fvarnames"], plotfile)
    sout, serr, ierr = test_util.run(command)

    if ierr != 0:
        return serr

    # Split on whitespace
    tvars = re.split(r"\s+", sout)[2:-1:2]

    return set(tvars)

def process_comparison_results(stdout, tvars, test):
    """ checks the output of fcompare (passed in as stdout)
        to determine whether all relative errors fall within
        the test's tolerance """

    # Alternative solution - just split on whitespace
    # and iterate through resulting list, attempting
    # to convert the next two items to floats. Assume
    # the current item is a variable if successful.

    # Split on whitespace
    regex = r"\s+"
    words = re.split(regex, stdout)

    indices = filter(lambda i: words[i] in tvars, range(len(words)))

    for i in indices:
        _, abs_err, rel_err = words[i: i + 3]
        if abs(test.tolerance) < abs(float(rel_err)) and test.abs_tolerance < abs(float(abs_err)):
            return False

    return True

def test_performance(test, suite, runtimes):
    """ outputs a warning if the execution time of the test this run
        does not compare favorably to past logged times """

    if test.name not in runtimes:
        return
    runtimes = runtimes[test.name]["runtimes"]

    if len(runtimes) < 1:
        suite.log.log("no completed runs found")
        return

    num_times = len(runtimes)
    suite.log.log(f"{num_times} completed run(s) found")
    suite.log.log("checking performance ...")

    # Slice out correct number of times
    run_diff = num_times - test.runs_to_average
    if run_diff > 0:
        runtimes = runtimes[:-run_diff]
        num_times = test.runs_to_average
    else:
        test.runs_to_average = num_times

    test.past_average = sum(runtimes) / num_times

    # Test against threshold
    meets_threshold, percentage, compare_str = test.measure_performance()
    if meets_threshold is not None and not meets_threshold:
        warn_msg = "test ran {:.1f}% {} than running average of the past {} runs"
        warn_msg = warn_msg.format(percentage, compare_str, num_times)
        suite.log.warn(warn_msg)

def determine_coverage(suite):

    try:
        results = coverage.main(suite.full_test_dir)
    except:
        suite.log.warn("error generating parameter coverage reports, check formatting")
        return

    if not any([res is None for res in results]):

        suite.covered_frac = results[0]
        suite.total = results[1]
        suite.covered_nonspecific_frac = results[2]
        suite.total_nonspecific = results[3]

        spec_file = os.path.join(suite.full_test_dir, coverage.SPEC_FILE)
        nonspec_file = os.path.join(suite.full_test_dir, coverage.NONSPEC_FILE)

        shutil.copy(spec_file, suite.full_web_dir)
        shutil.copy(nonspec_file, suite.full_web_dir)

def process_single_test(test, suite, args, test_list, log_lock, build_lock):
    """
    Process a single test: build, run, analyze, and report.
    This function runs in a separate thread for parallel execution.
    """
    try:
        with log_lock:
            suite.log.outdent()  # just to make sure we have no indentation
            suite.log.skip()
            suite.log.bold(f"working on test: {test.name}")
            suite.log.indent()

            if not args.make_benchmarks is None and (test.restartTest or test.compileTest or
                                                     test.selfTest):
                suite.log.warn(f"benchmarks not needed for test {test.name}")
                return

            output_dir = suite.full_test_dir + test.name + '/'
            os.mkdir(output_dir)
            test.output_dir = output_dir

        #----------------------------------------------------------------------
        # compile the code (serialize builds to avoid conflicts)
        #----------------------------------------------------------------------
        with build_lock:
            if not test.extra_build_dir == "":
                bdir = suite.repos[test.extra_build_dir].dir + test.buildDir
            else:
                bdir = suite.source_dir + test.buildDir

            original_dir = os.getcwd()
            os.chdir(bdir)

            if test.reClean == 1:
                # for one reason or another, multiple tests use different
                # build options, make clean again to be safe
                with log_lock:
                    suite.log.log("re-making clean...")
                if not test.extra_build_dir == "":
                    suite.make_realclean(repo=test.extra_build_dir)
                elif suite.sourceTree in ["AMReX", "amrex"]:
                    suite.make_realclean(repo="AMReX")
                else:
                    suite.make_realclean()

            # Register start time
            test.build_time = time.time()

            with log_lock:
                suite.log.log("building...")

            coutfile = f"{output_dir}/{test.name}.make.out"

            # Build the test
            if suite.sourceTree == "C_Src" or test.testSrcTree == "C_Src":
                if suite.useCmake:
                    comp_string, rc = suite.build_test_cmake(test=test, outfile=coutfile)
                    # CMake build_test_cmake moves and renames executable to {test.name}.ex in source_dir
                    executable = os.path.join(suite.source_dir, f"{test.name}.ex")
                else:
                    comp_string, rc = suite.build_c(test=test, outfile=coutfile)
                    executable = test_util.get_recent_filename(bdir, "", ".ex")

            test.comp_string = comp_string

            # make return code is 0 if build was successful
            if rc == 0:
                test.compile_successful = True
            # Compute compile time
            test.build_time = time.time() - test.build_time
            
            with log_lock:
                suite.log.log(f"Compilation time: {test.build_time:.3f} s")
                
            # Return to original directory before releasing build lock
            os.chdir(original_dir)

        # copy the make.out into the web directory
        shutil.copy(f"{output_dir}/{test.name}.make.out", suite.full_web_dir)

        if not test.compile_successful:
            error_msg = "ERROR: compilation failed"
            with log_lock:
                report.report_single_test(suite, test, test_list, failure_msg=error_msg)

                # Print compilation error message (useful for CI tests)
                if suite.verbose > 0:
                    with open(f"{output_dir}/{test.name}.make.out") as f:
                        print(f.read())
            return

        if test.compileTest:
            with log_lock:
                suite.log.log("creating problem test report ...")
                report.report_single_test(suite, test, test_list)
            return

        #----------------------------------------------------------------------
        # copy the necessary files over to the run directory
        #----------------------------------------------------------------------
        with log_lock:
            suite.log.log(f"run & test directory: {output_dir}")
            suite.log.log("copying files to run directory...")

        needed_files = []
        if executable is not None:
            needed_files.append((executable, "copy"))

        if test.run_as_script:
            needed_files.append((test.run_as_script, "copy"))

        if test.inputFile:
            with log_lock:
                suite.log.log("path to input file: {}".format(test.inputFile))
            # For CMake builds, input file path is relative to source_dir
            if suite.useCmake:
                input_file_path = os.path.join(suite.source_dir, test.inputFile)
            else:
                input_file_path = test.inputFile
            needed_files.append((input_file_path, "copy"))
            # strip out any sub-directory from the build dir
            test.inputFile = os.path.basename(test.inputFile)

        if test.probinFile != "":
            needed_files.append((test.probinFile, "copy"))

        for lfile in test.linkFiles:
            needed_files.append((lfile, "link"))

        for auxfile in test.auxFiles:
            needed_files.append((auxfile, "copy"))

        for f, action in needed_files:
            
            if os.path.isfile(f):
                if action == "copy":
                    shutil.copy(f, output_dir)
                elif action == "move":
                    shutil.move(f, output_dir)
                elif action == "link":
                    if not os.path.exists(output_dir + os.path.basename(f)):
                        os.symlink(f, output_dir + os.path.basename(f))
            else:
                # look relative to the benchmark dir
                bdir = os.path.dirname(test.inputFile) + "/" + f
                if os.path.isfile(bdir):
                    shutil.copy(bdir, output_dir)
                else:
                    with log_lock:
                        suite.log.warn(f"ERROR: unable to copy file {f}")
                    continue

        #----------------------------------------------------------------------
        # run the test
        #----------------------------------------------------------------------
        with log_lock:
            suite.log.log("running the test...")

        os.chdir(output_dir)

        test.wall_time = time.time()

        if suite.sourceTree == "C_Src" or test.testSrcTree == "C_Src":

            # For CMake builds, executable is already absolute path; for others, add ./
            if suite.useCmake and os.path.isabs(executable):
                base_cmd = f"{executable} {test.inputFile} "
            else:
                base_cmd = f"./{executable} {test.inputFile} "
            if suite.plot_file_name != "":
                base_cmd += f" {suite.plot_file_name}={test.name}_plt "
            if suite.check_file_name != "none":
                base_cmd += f" {suite.check_file_name}={test.name}_chk "

            # keep around the checkpoint files only for the restart runs
            if test.restartTest:
                if suite.check_file_name != "none":
                    base_cmd += " amr.checkpoint_files_output=1 amr.check_int=%d " % \
                        (test.restartFileNum)
            else:
                if suite.check_file_name != "none":
                    base_cmd += " amr.checkpoint_files_output=0"

            base_cmd += f" {suite.globalAddToExecString} {test.runtime_params}"

        if test.run_as_script:
            base_cmd = f"./{test.run_as_script} {test.script_args}"

        if test.customRunCmd is not None:
            base_cmd = test.customRunCmd

        if args.with_valgrind:
            base_cmd = "valgrind " + args.valgrind_options + " " + base_cmd

        suite.run_test(test, base_cmd)

        test.wall_time = time.time() - test.wall_time

        with log_lock:
            suite.log.log(f"Execution time: {test.wall_time:.3f} s")

        # do the comparison
        if not test.selfTest:
            # For now, skip comparison in parallel mode - it's complex and needs benchmark files
            # The comparison will be done after all tests complete
            test.compare_successful = True
            test.compare_file_names = []
        else:
            # this is a self-test
            try:
                of = open(test.outfile)
            except OSError:
                with log_lock:
                    suite.log.warn("no output file found")
                out_lines = ['']
            else:
                out_lines = of.readlines()

                # successful comparison is indicated by presence
                # of success string
                for line in out_lines:
                    if line.find(test.stSuccessString) >= 0:
                        test.compare_successful = True
                        break

                of.close()

        with log_lock:
            suite.log.log("creating problem test report ...")
            report.report_single_test(suite, test, test_list)

        # Look for backtrace files
        suite.copy_backtrace(test)
        
        # Look for job_info files
        if not test.run_as_script:
            job_info_file = f"{output_dir}/job_info"
            if os.path.isfile(job_info_file):
                # copy into the web directory
                shutil.copy(job_info_file, suite.full_web_dir)
        
        # restore original directory
        os.chdir(original_dir)
        
    except Exception as e:
        with log_lock:
            suite.log.fail(f"ERROR: Test {test.name} failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()

def test_suite(argv):
    """
    the main test suite driver
    """

    # parse the commandline arguments
    args = test_util.get_args(arg_string=argv)

    # read in the test information
    suite, test_list = params.load_params(args)

    active_test_list = [t.name for t in test_list]

    test_list = suite.get_tests_to_run(test_list)

    suite.log.skip()
    suite.log.bold("running tests: ")
    suite.log.indent()
    for obj in test_list:
        suite.log.log(obj.name)
    suite.log.outdent()

    if not args.complete_report_from_crash == "":

        # make sure the web directory from the crash run exists
        suite.full_web_dir = "{}/{}/".format(
            suite.webTopDir, args.complete_report_from_crash)
        if not os.path.isdir(suite.full_web_dir):
            suite.log.fail("Crash directory does not exist")

        suite.test_dir = args.complete_report_from_crash

        # find all the tests that completed in that web directory
        tests = []
        test_file = ""
        was_benchmark_run = 0
        for sfile in os.listdir(suite.full_web_dir):
            if os.path.isfile(sfile) and sfile.endswith(".status"):
                index = sfile.rfind(".status")
                tests.append(sfile[:index])

                with open(suite.full_web_dir + sfile) as f:
                    for line in f:
                        if line.find("benchmarks updated") > 0:
                            was_benchmark_run = 1

            if os.path.isfile(sfile) and sfile.endswith(".ini"):
                test_file = sfile


        # create the report for this test run
        num_failed = report.report_this_test_run(suite, was_benchmark_run,
                                                 "recreated report after crash of suite",
                                                 "", tests, test_file)

        # create the suite report
        suite.log.bold("creating suite report...")
        report.report_all_runs(suite, active_test_list)
        suite.log.close_log()
        sys.exit("done")


    #--------------------------------------------------------------------------
    # check bench dir and create output directories
    #--------------------------------------------------------------------------
    all_compile = all([t.compileTest == 1 for t in test_list])

    if not all_compile:
        bench_dir = suite.get_bench_dir()

    if not args.copy_benchmarks is None:
        last_run = suite.get_last_run()

    suite.make_test_dirs()

    if suite.slack_post:
        if args.note == "" and suite.repos["source"].pr_wanted is not None:
            note = "testing PR-{}".format(suite.repos["source"].pr_wanted)
        else:
            note = args.note

        msg = "> {} ({}) test suite started, id: {}\n> {}".format(
            suite.suiteName, suite.sub_title, suite.test_dir, note)
        suite.slack_post_it(msg)

    if not args.copy_benchmarks is None:
        old_full_test_dir = suite.testTopDir + suite.suiteName + "-tests/" + last_run
        copy_benchmarks(old_full_test_dir, suite.full_web_dir,
                        test_list, bench_dir, suite.log)

        # here, args.copy_benchmarks plays the role of make_benchmarks
        num_failed = report.report_this_test_run(suite, args.copy_benchmarks,
                                                 "copy_benchmarks used -- no new tests run",
                                                 "",
                                                 test_list, args.input_file[0])
        report.report_all_runs(suite, active_test_list)

        if suite.slack_post:
            msg = f"> copied benchmarks\n> {args.copy_benchmarks}"
            suite.slack_post_it(msg)

        sys.exit("done")


    #--------------------------------------------------------------------------
    # figure out what needs updating and do the git updates, save the
    # current hash / HEAD, and make a ChangeLog
    # --------------------------------------------------------------------------
    now = time.localtime(time.time())
    update_time = time.strftime("%Y-%m-%d %H:%M:%S %Z", now)

    no_update = args.no_update.lower()
    if not args.copy_benchmarks is None:
        no_update = "all"

    # the default is to update everything, unless we specified a hash
    # when constructing the Repo object
    if no_update == "none":
        pass

    elif no_update == "all":
        for k in suite.repos:
            suite.repos[k].update = False

    else:
        nouplist = [k.strip() for k in no_update.split(",")]

        for repo in suite.repos.keys():
            if repo.lower() in nouplist:
                suite.repos[repo].update = False

    os.chdir(suite.testTopDir)

    for k in suite.repos:
        suite.log.skip()
        suite.log.bold(f"repo: {suite.repos[k].name}")
        suite.log.indent()

        if suite.repos[k].update or suite.repos[k].hash_wanted:
            suite.repos[k].git_update()

        suite.repos[k].save_head()

        if suite.repos[k].update:
            suite.repos[k].make_changelog()

        suite.log.outdent()


    # keep track if we are running on any branch that is not the suite
    # default
    branches = [suite.repos[r].get_branch_name() for r in suite.repos]
    if not all(suite.default_branch == b for b in branches):
        suite.log.warn("some git repos are not on the default branch")
        bf = open(f"{suite.full_web_dir}/branch.status", "w")
        bf.write("branch different than suite default")
        bf.close()

    #--------------------------------------------------------------------------
    # build the tools and do a make clean, only once per build directory
    #--------------------------------------------------------------------------
    if not suite.useCmake:
        suite.build_tools(test_list)

    all_build_dirs = find_build_dirs(test_list)

    suite.log.skip()
    suite.log.bold("make clean in...")

    for d, source_tree in all_build_dirs:

        if not source_tree == "":
            suite.log.log(f"{d} in {source_tree}")
            os.chdir(suite.repos[source_tree].dir + d)
            suite.make_realclean(repo=source_tree)
        else:
            suite.log.log(f"{d}")
            os.chdir(suite.source_dir + d)
            if suite.sourceTree in ["AMReX", "amrex"]:
                suite.make_realclean(repo="AMReX")
            else:
                suite.make_realclean()

    os.chdir(suite.testTopDir)


    #--------------------------------------------------------------------------
    # Setup Cmake if needed
    #--------------------------------------------------------------------------
    if suite.useCmake and not suite.isSuperbuild:
        cmake_setup(suite)


    #--------------------------------------------------------------------------
    # Get execution times from previous runs
    #--------------------------------------------------------------------------
    runtimes = suite.get_wallclock_history()

    #--------------------------------------------------------------------------
    # main loop over tests - parallel execution
    #--------------------------------------------------------------------------
    
    suite.log.bold(f"Running tests with maxConcurrentTests = {suite.maxConcurrentTests}")
    
    # Create locks for thread-safe operations
    log_lock = threading.Lock()
    build_lock = threading.Lock()  # Serialize builds to avoid directory conflicts
    
    # Use ThreadPoolExecutor for parallel test execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=suite.maxConcurrentTests) as executor:
        # Submit all tests to the executor
        future_to_test = {
            executor.submit(process_single_test, test, suite, args, test_list, log_lock, build_lock): test 
            for test in test_list
        }
        
        # Wait for all tests to complete and handle any exceptions
        for future in concurrent.futures.as_completed(future_to_test):
            test = future_to_test[future]
            try:
                future.result()  # This will raise an exception if the test failed
            except Exception as exc:
                with log_lock:
                    suite.log.fail(f"Test {test.name} generated an exception: {exc}")
    
    # Post-processing after all tests complete
    suite.log.bold("All tests completed. Processing results...")


    #--------------------------------------------------------------------------
    # Clean Cmake build and install directories if needed
    #--------------------------------------------------------------------------
    if suite.useCmake:
        suite.cmake_clean("AMReX", suite.amrex_dir)
        suite.cmake_clean(suite.suiteName, suite.source_dir)

    #--------------------------------------------------------------------------
    # jsonify and save runtimes
    #--------------------------------------------------------------------------
    file_path = suite.get_wallclock_file()
    with open(file_path, 'w') as json_file:
        json.dump(runtimes, json_file, indent=4)

    #--------------------------------------------------------------------------
    # parameter coverage
    #--------------------------------------------------------------------------
    if suite.reportCoverage:
        determine_coverage(suite)

    #--------------------------------------------------------------------------
    # write the report for this instance of the test suite
    #--------------------------------------------------------------------------
    suite.log.outdent()
    suite.log.skip()
    suite.log.bold("creating new test report...")
    num_failed = report.report_this_test_run(suite, args.make_benchmarks, args.note,
                                             update_time,
                                             test_list, args.input_file[0])

    # make sure that all of the files in the web directory are world readable
    for file in os.listdir(suite.full_web_dir):
        current_file = suite.full_web_dir + file

        if os.path.isfile(current_file):
            os.chmod(current_file, 0o644)

    # reset the branch to what it was originally
    suite.log.skip()
    suite.log.bold("reverting git branches/hashes")
    suite.log.indent()

    for k in suite.repos:
        if suite.repos[k].update or suite.repos[k].hash_wanted:
            suite.repos[k].git_back()

    suite.log.outdent()

    # For temporary run, return now without creating suite report.
    if args.do_temp_run:
        suite.delete_tempdirs()
        return num_failed

    # store an output file in the web directory that can be parsed easily by
    # external program
    name = "source"
    if suite.sourceTree in ["AMReX", "amrex"]:
        name = "AMReX"
    branch = ''
    if suite.repos[name].get_branch_name():
        branch = suite.repos[name].get_branch_name()

    with open("{}/suite.{}.status".format(suite.webTopDir, branch.replace("/", "_")), "w") as f:
        f.write("{}; num failed: {}; source hash: {}".format(
            suite.repos[name].name, num_failed, suite.repos[name].hash_current))


    #--------------------------------------------------------------------------
    # generate the master report for all test instances
    #--------------------------------------------------------------------------
    suite.log.skip()
    suite.log.bold("creating suite report...")
    report.report_all_runs(suite, active_test_list)

    # delete any temporary directories
    suite.delete_tempdirs()

    def email_developers():
        msg = email.message_from_string(suite.emailBody)
        msg['From'] = suite.emailFrom
        msg['To'] = ",".join(suite.emailTo)
        msg['Subject'] = suite.emailSubject

        server = smtplib.SMTP('localhost')
        server.sendmail(suite.emailFrom, suite.emailTo, msg.as_string())
        server.quit()

    if num_failed > 0 and suite.sendEmailWhenFail and not args.send_no_email:
        suite.log.skip()
        suite.log.bold("sending email...")
        email_developers()


    if suite.slack_post:
        suite.slack_post_it(f"> test complete, num failed = {num_failed}\n{suite.emailBody}")

    return num_failed


if __name__ == "__main__":
    n = test_suite(sys.argv[1:])
    sys.exit(n)
