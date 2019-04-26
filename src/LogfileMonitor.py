#!/usr/bin/env python3
# -*- coding:utf8 -*-
"""
###################################################################################################
# changes :                                                                                       #
# 20190301-XJS : Initial   supports Python 3.5                                                    #
# 20190408-XJS :           supports both RUN and READ mode                                        #
# 20190412-XJS : 1.0       READ mode runs for once and then exit                                  #
# 20190414-XJS : 1.0       Improved, E.g remove RC_FILE                                           #
# 20190422-XJS : 1.0       Improvement for RTC:501606                                             #
# 20190424-XJS : 1.0       Process errors and use the same output                                 #
###################################################################################################
# Search the pattern from the monitored log file/s, and generate the output with defined format

"""
import copy
import logging
import os
import re
import sys
import time
import subprocess
import yaml

VERSION = "1.0 20190424"

SCRIPT_NAME = os.path.basename(__file__)

# define the output format of RUN mode
RUN_OUTPUT_FORMAT = {
    "logicalname": "http-server-log",
    "timestamp": 0,
    "readout": "N",
    "logfilename": "/var/log/http.log",
    "instance": "http",
    "rc": 0,
    "rcdesc": "Successful",
    "message": "2019-03-08 21:05:49,947 - ERROR - HTTP server failed to start",
    "sevmap": "Critical",
    "actualnumberofhits": 5,
    "maxnumberofhits": 1,
    "ttl": 0,
    "logeventtype": "InitializationError",
    "logfield1": "",
    "logfield2": "",
    "resource": "http:/var/log/http.log:InitializationError:field1:field2",
    "tag": "Support Application 001"
}

# Set the interval for RUN mode, unit is second
SCRIPT_INTERVAL_RUN = 5

# Set Return code & description
RETURN_CODE_DESC = [
    {"rc": "0", "desc": "Successful"},
    {"rc": "1", "desc": "Config file does not exist"},
    {"rc": "2", "desc": "The output file of RUN mode does not exist"},
    {"rc": "3", "desc": "The usage of command line is invalid"},
    {"rc": "4", "desc": "The file does not apply YAML format"},
    {"rc": "5", "desc": "Parameter is missing/invalid in config file"},
    {"rc": "7", "desc": "Process is already running"},
    {"rc": "9", "desc": "Field is missing or invalid in output file of RUN mode"},
    {"rc": "21", "desc": "There is not any matched logfiles found"},
    {"rc": "99", "desc": "Undefined error message"},
    {"rc": "100", "desc": "The function is not supported for now"}
]

# Set the output format of READ mode
READ_OUTPUT_FORMAT = {
    "separator": ";;",
    "fields": "rc rcdesc "
              "logicalname instance logfilename message sevmap "
              "actualnumberofhits maxnumberofhits ttl "
              "logeventtype logfield1 logfield2 resource tag timestamp"
}
#
# # Set default file of READ mode
# OUT_FILE = os.path.join(WORKING_DIR, "LogfileMonitorOut.yml")

# Set debugging or not
DEBUG = "1"

if DEBUG == "1":
    logging.basicConfig(filename='/tmp/%s' % SCRIPT_NAME.replace(".py", ".log"),
                        level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(filename='/tmp/%s' % SCRIPT_NAME.replace(".py", ".log"),
                        level=logging.WARNING,
                        format='%(asctime)s - %(levelname)s - %(message)s')


def usage():
    print("Usage is:")
    print("          %s -m {run | read} -p <Parameter file> [-o <Output file>]" % SCRIPT_NAME)
    print("      or: %s -v" % SCRIPT_NAME)
    print("      or: %s -h" % SCRIPT_NAME)
    print("")
    print("    -m {run | read}  Required, with RUN or READ mode")
    print(
        "    -p <Parameter file>  Required, the FULL path of parameter file, e.g /home/em7admin/LogfileMonitorPara.yml")
    print(
        '    -o <Output file>  Optional, the output file, default is LogfileMonitorOut.yml with the same directory of "-p"')
    print("    -v  Show the current version information")
    print("    -h  Show the usage of the script")


def get_argv_dict(argv):
    """
    Save all the parameters into variable
    :return: otpd
    """
    optd = {"script": argv[0]}
    argv = argv[1:]

    while argv:
        if len(argv) >= 2:
            optd[argv[0]] = argv[1]
            argv = argv[2:]
        elif argv[0] == "-v" or argv[0] == "-h":
            # "-v" has not any parameter following up
            optd[argv[0]] = ""
            argv = argv[1:]
        # elif argv[0] == "-h":
        #     usage()
        else:
            RC = 3
            raise SystemExit(RC)
    return optd


def get_from_yaml(file):
    """
    Capture the data from YAML file to a variable
    :global: OUT_ITEM_SAMPLE
    :param file: file
    :return: filed
    """

    global OUT_ITEM_SAMPLE
    filed = {}
    # Will capture the data from file to a variable
    logging.info("Capture the data from file: (%s)" % file)
    try:
        with open(file) as f:
            filed = yaml.load(f)
    except IOError:
        logging.error("File access error: %s" % file)

        RC = 1
        OUT_ITEM_SAMPLE["rc"] = RC
        write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file
        OUT_ITEM_SAMPLE["rc"] = ""

    return filed


def trans_pattern_logfile(mylist_1):
    """
    Translate the search pattern to the exact logfilename/s from the regexp if have
    :param mylist_1:
    :return: mylist_2
    """
    global OUT_ITEM_SAMPLE

    logging.debug("To be translated search pattern with regexp logfilenames:")
    # for i in range(len(mylist_1)):
    #     logging.debug(mylist_1[i])
    for item in mylist_1:
        logging.debug(item)
    mylist_2 = []

    for i in range(len(mylist_1)):
        match_yn = False
        # Save the item of pattern search for logfilename regexp
        item_logfilename = copy.deepcopy(mylist_1[i])

        # Get the filename and dir name
        logging.debug("logfilename regexp is: %s" % item_logfilename["logfilename"])

        file_exp = os.path.basename(item_logfilename["logfilename"])
        dir_exp = os.path.dirname(item_logfilename["logfilename"]) \
            if os.path.dirname(item_logfilename["logfilename"]) else "./"

        for f in os.listdir(dir_exp):
            file = os.path.join(dir_exp, f)
            if os.path.isfile(file):
                # check with expr
                res = re.match(file_exp, f)
                if res:
                    match_yn = True
                    matched_file = os.path.join(dir_exp, res.group(0))

                    logging.debug("Matched file: %s" % matched_file)

                    # Update and/or Add logfilename
                    item_logfilename["logfilename"] = matched_file
                    # Append it

                    mylist_2.append(copy.deepcopy(item_logfilename))
        if not match_yn:
            RC = 21
            logging.error("No matched logfile for: %s" % item_logfilename["logfilename"])
            # write the wrong message to output

            OUT_ITEM_SAMPLE = copy.deepcopy(item_logfilename)
            # set the return code for "NO MATCHED LOGFILE FOUND"
            OUT_ITEM_SAMPLE["rc"] = RC
            write_data_outfile(OUT_ITEM_SAMPLE)

    return mylist_2


def trans_param_pattern(mylist_1, mylist_2):
    """
    Translate the parameters to every pattern
    :param mylist_1:
    :param mylist_2:
    :return: mylist_2
    """
    logging.debug("To be translated data:")
    for i in range(len(mylist_1)):
        logging.debug(mylist_1[i])

    for i in range(len(mylist_1)):
        item = copy.deepcopy(mylist_1[i])
        mydict = {}
        for k in item.keys():
            if k != "patternmatch":
                mydict[k] = item[k]

        for j in range(len(item["patternmatch"])):
            mydict2 = copy.deepcopy(mydict)

            pattern = item["patternmatch"][j]
            for k in pattern.keys():
                mydict2[k] = pattern[k]

            # Append the data into mylist_2
            mylist_2.append(mydict2)

    logging.debug("translated data:")
    for i in range(len(mylist_2)):
        logging.debug(mylist_2[i])

    return mylist_2


def write_data_outfile(out_item):
    """
    Append the data to OUT_FILE
    :param out_item: new data
    : Global: OUT_FILE, RETURN_CODE_DESC
    :return: Update OUT_FILE
    """

    global OUT_FILE, RETURN_CODE_DESC
    # Get rcdesc relies on rc from list of RETURN_CODE_DESC

    return_code = str(out_item["rc"])  # while rc is interger data type
    if return_code:
        out_item["rcdesc"] = "RC is not defined"  # If it is missing in configuration

        for i in range(len(RETURN_CODE_DESC)):
            rc = RETURN_CODE_DESC[i]["rc"]
            rcdesc = RETURN_CODE_DESC[i]["desc"]
            if return_code == rc:
                out_item["rcdesc"] = rcdesc
                break

    # Set default values if missing
    if not out_item.get("timestamp"):
        out_item["timestamp"] = int(time.time())  # Set timestamp
    if not out_item.get("readout"):
        out_item["readout"] = "N"  # set it as default

    # Update the output contents if there is relevant item from parameter file
    if not out_item.get("logeventtype"):
        out_item["logeventtype"] = out_item["eventtype"] if out_item.get("eventtype") else ""

    if not out_item.get("resource"):
        out_item["resource"] = "%s:%s:%s:%s:%s" % \
                               (out_item.get("instance", ""),
                                out_item.get("logfilename", ""),
                                out_item.get("eventtype", ""),
                                out_item.get("logfield1", ""),
                                out_item.get("logfield2", "")
                                )

    # if there is not any matched contents
    if not out_item.get("message"):
        out_item["message"] = out_item.get("matched_contents", "")

    if not out_item.get("tag"):
        out_item["tag"] = out_item.get("responsible", "")

    if not out_item.get("actualnumberofhits"):
        out_item["actualnumberofhits"] = 0

    # Update the message with line's content

    # Append the new item into OUT_FILE
    out_data = [out_item]

    result = yaml.dump(out_data, default_flow_style=False)

    with open(OUT_FILE, "a") as f:
        f.write(result)

    return


def check_required_parameters(mydict, keys):
    """
    Check if the Required parameters are provided or not
    :param mydict: To be checked dictionary data
    :param keys: The list of parameters
    :return: Null or a string of the missing key/s
    """
    str1 = ""
    for key in keys:
        if not mydict.get(key):
            str1 = str1 + "&" + key
    str1 = str1.strip("&")
    return str1


def check_valid_parameters(mydict, keys):
    """
    Check if the provided parameters are valid ( either Required or Optional)
    :param mydict: To be checked dirctionary data
    :param keys: The list of parameters
    :return: Null or a string of the invalid key/s
    """
    str1 = ""
    for key in mydict.keys():
        if key not in keys:
            str1 = str1 + "&" + key
    str1 = str1.strip("&")
    return str1


def valid_para_config_file(mydict):
    """
    Check the parameters in config file (e.g LogfileMonitorParam.yml)
    :param mydict: The extracted data from config file
    :return: Null or a string of the invalid key/s
    """
    # str1 = ""
    script_exit = False
    # The required parameters
    para = ["logfilename", "logicalname", "instance", "eventtype", "readtype", "rotation", "deduplicate", "occurences",
            "responsible"]

    str1 = check_required_parameters(mydict, para)
    if str1:
        script_exit = True
        RC = 5
        str1 = "Missing: %s" % str1

    # The Optional parameters
    para2 = []

    str2 = check_valid_parameters(mydict, para + para2)
    if str2:
        str2 = "Invalid: %s" % str2
    str1 += " && %s" % str2

    # To validate the contents for specific fields
    keys = mydict.keys()

    if "readtype" in keys:
        val_readtype = mydict["readtype"].lower()
        if val_readtype not in ["incremental", "full"]:
            str1 += " && Invalid: %s" % "readtype"
            # Script will exit with error
            script_exit = True
            RC = 5

    if "deduplicate" in keys:
        val_readtype = mydict["deduplicate"].lower()
        if val_readtype not in ["y", "n"]:
            str1 += " && Invalid: %s" % "deduplicate"
            # Script will exit with error
            script_exit = True
            RC = 5

    if "rotation" in keys:
        val_readtype = mydict["rotation"].lower()
        if val_readtype not in ["y", "n", "delete"]:
            str1 += " && Invalid: %s" % "rotation"
            script_exit = True
            RC = 5

    # Check the properties for patternmatch collection
    for i in range(len(mydict["patternmatch"])):
        item = mydict["patternmatch"][i]
        if "patternsearchtype" in item.keys():
            val_readtype = item["patternsearchtype"].lower()
            if val_readtype not in ["starts with", "ends with", "substring", "exactly", "regexp"]:
                str1 += " && Invalid: %s" % "patternsearchtype"
                script_exit = True
                RC = 5

        if "alarmonerror" in item.keys():
            val_readtype = item["alarmonerror"].lower()
            if val_readtype not in ["y", "n"]:
                str1 += " && Invalid: %s" % "alarmonerror"
                # Script will exit with error
                script_exit = True
                RC = 5

    if script_exit:
        logging.error("Parameter is missing/invalid from config file: %s" % str1)

        OUT_ITEM_SAMPLE["rc"] = RC
        write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file

        raise SystemExit(RC)

    return str1


def valid_yaml_format(filename, dump_data, valid_type):
    """
    Check if the dump data from filename is valid for type of 'valid_type'
    :param filename:
    :param dump_data:
    :param valid_type: Type of either list or dict
    :return:
    """
    global OUT_ITEM_SAMPLE
    #
    # Check if the YAML file is valid (list data type)
    if valid_type == "list":
        if not isinstance(dump_data, list):
            RC = 4
            logging.error("YAML file format is invalid: %s" % filename)

            OUT_ITEM_SAMPLE["rc"] = RC
            # write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file

            raise SystemExit(RC)

    elif valid_type == "dict":
        if not isinstance(dump_data, dict):
            RC = 4
            logging.error("YAML file format is invalid: %s" % filename)

            OUT_ITEM_SAMPLE["rc"] = RC
            # write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file

            raise SystemExit(RC)

    return


def process_already_running(process_name):
    """
    If the process (no case sensitive) is already running or not
    Check for Linux platform only FOR NOW
    :param process_name: The process identified by "ps -ef"
    :return: Boolean, True or False
    """
    p = subprocess.Popen(['ps', '-ef'], stdout=subprocess.PIPE)
    out, err = p.communicate()

    process_duplicate = False
    process_running = False
    for line in out.splitlines():
        line = str(line, encoding='utf-8').lower()
        if process_name.lower() in str(line):
            if not process_running:
                # For the first discovered running process
                # Get the pid and ppid for 'ps aux'
                pid = int(line.split()[1])
                ppid = int(line.split()[2])
                process_running = True

            else:
                pid2 = int(line.split()[1])
                ppid2 = int(line.split()[2])
                if pid2 == ppid or ppid2 == pid:
                    # Skip for the process is the parent or child of first discovered process
                    continue
                else:
                    process_duplicate = True
                    break
                    # It is NOT the first discovered running process
    return process_duplicate


def main():
    global PARAM_FILE, OUT_FILE
    global OUT_ITEM_SAMPLE, SCRIPT_INTERVAL_RUN

    # global FORMAT_FILE
    global READ_OUTPUT_FORMAT, RUN_OUTPUT_FORMAT

    try:
        # Get args
        argv = sys.argv
        logging.debug(argv)
        mydict = get_argv_dict(argv)

        # Return the version
        if "-v" in mydict.keys():
            print(VERSION)
            RC = 0
            raise SystemExit(RC)

        # Return the usage
        if "-h" in mydict.keys():
            usage()
            RC = 0
            raise SystemExit(RC)

        # Check the required parameter/s
        para = ["-m", "-p"]
        if check_required_parameters(mydict, para):
            logging.error("The required parameter is missing: %s" % check_required_parameters(mydict, para))
            RC = 1
            raise SystemExit(RC)

        # check if there is any unsupported parameter
        para = ["script", "-m", "-p", "-v", "-h", "-o"]
        for i in mydict.keys():
            found_yn = False
            for item in para:
                if i == item:
                    found_yn = True
                    break
            if not found_yn:
                # If any key is not found
                RC = 3
                raise SystemExit(RC)

        PARAM_FILE = mydict.get("-p")

        # Get the directory of parameter file as the working directory
        WORKING_DIR = os.path.split(PARAM_FILE)[0] if os.path.split(PARAM_FILE)[0] else "./"

        # Check if the parameter file exists
        if not os.path.isfile(PARAM_FILE):
            RC = 1
            raise SystemExit(RC)

        # Set the output file of RUN mode
        OUT_FILE = os.path.join(WORKING_DIR, "LogfileMonitorOut.yml")

        # validate the value of "-m", it should be either RUN or READ
        script_mode = mydict.get("-m").lower()
        if script_mode not in ["run", "read"]:
            logging.error("The value of '- m' is not valid: %s" % script_mode)
            RC = 3
            raise SystemExit(RC)

        # create the file to save the number of last checked line for every logfile
        LAST_CHECKED_LINE = os.path.join(WORKING_DIR, "%s" % SCRIPT_NAME.replace(".py", ".loc"))

        # Create a new one if it does not exist
        if not os.path.isfile(LAST_CHECKED_LINE):
            with open(LAST_CHECKED_LINE, 'w') as f:
                f.write("logicalname     logfilename      0\n")

        OUT_ITEM_SAMPLE = {}

        RC = 0
        while True:
            if script_mode == "run":
                # exit if another deamon/process is already running for 'run'
                names = ["LogfileMonitor -m run", "LogfileMonitor.py -m run"]
                for name in names:
                    if sys.platform == "linux":
                        if process_already_running(name):
                            logging.error("The process(%s) is already running, Please verify with 'ps -f' command!!!" % name)
                            RC = 7
                            raise SystemExit(RC)
                    else:
                        logging.error("It is not supported to check the running process on other platforms")
                        RC = 100
                        raise SystemExit(RC)

                out_data_item = RUN_OUTPUT_FORMAT
                # Clear the data, and only keep the keys and default values, and save it as output sample data
                for k in out_data_item.keys():
                    if k not in ["actualnumberofhits", "maxnumberofhits", "ttl"]:
                        OUT_ITEM_SAMPLE[k] = ""
                    else:
                        # Set 0 for Interger type data
                        OUT_ITEM_SAMPLE[k] = 0

                # Get parameters from file
                mylist_param = get_from_yaml(PARAM_FILE)
                logging.debug("data for parameter file:\n %s" % mylist_param)
                # Check if the YAML file is valid (list data type)
                valid_yaml_format(PARAM_FILE, mylist_param, "list")

                # Check if the parameters are valid
                for i in range(len(mylist_param)):
                    valid_para_config_file(mylist_param[i])

                # Translate the parameters to every patternsearch
                mylist_pattern = []
                mylist_pattern = trans_param_pattern(mylist_param, mylist_pattern)
                logging.debug("data for patterns:\n%s" % mylist_pattern)

                # debugging: list out all the search patterns
                logging.debug("All the search patterns with exact logfilename expresion:")
                for i in range(len(mylist_pattern)):
                    logging.debug(mylist_pattern[i])

                # Translate the regexp in logfilename to the exact logfilename/s
                mylist_logfile = trans_pattern_logfile(mylist_pattern)

                if len(mylist_logfile) == 0:
                    logging.warning("There is not any exactly match logfilename.")
                else:
                    logging.debug("All the search patterns with exact logfilename:")
                    for i in range(len(mylist_logfile)):
                        logging.debug(mylist_logfile[i])

                    """
                    ###
                    # Search pattern in the specific logfile
                    #
                    # Useful keys for searching are:
                    #     logfilename, patternsearch, patternsearchtype ???
                    # also depends on:
                    #     readtype: Full/Increment
                    #
                    # The match pattern will add into global variable:out_data (a list which contains dictionary type data)
                    """
                    last_line_list = []

                    for i in range(len(mylist_logfile)):
                        # Process for every monitored logfile
                        mylist_logfile_entry = mylist_logfile[i]

                        logfilename = mylist_logfile_entry["logfilename"]  # exact logfile name with path
                        search_type = mylist_logfile_entry.get("patternsearchtype", "substring").lower()
                        search_str = mylist_logfile_entry["patternsearch"]  # regural expression
                        read_type = mylist_logfile_entry["readtype"].lower()  # incremental/full

                        logging.debug("Start to search: \npatternsearch: %s  readtype: %s \nlogfilename: %s"
                                      % (search_str, read_type, logfilename))
                        matched_lines = []  # Record the matched lines' contents, an item per matched line' content
                        # The data should like:
                        # [{line: $line}, {line: $line}]

                        # Get the number of last checked lines from file: LAST_CHECKED_LINE
                        last_number = 0
                        logicalname = mylist_logfile_entry["logicalname"]
                        logfilename = mylist_logfile_entry["logfilename"]
                        with open(LAST_CHECKED_LINE, 'r') as f:
                            for line in f:

                                if len(line.split()) >= 3:
                                    if line.split()[0] == logicalname and line.split()[1] == logfilename:
                                        # The first field is the logfile name
                                        last_number = int(line.split()[2])
                                        break
                                else:
                                    logging.warning(
                                        "There not so many fields defined in file(>=3): %s" % LAST_CHECKED_LINE)

                        # search the pattern in logfilename
                        logging.debug("Search the pattern in logfilename")

                        with open(logfilename, 'r') as f:
                            # skip to the last checked line for "readtype: incremental"
                            logging.debug("Skip to the last checked line")
                            if read_type == "incremental":
                                for ii in range(0, last_number):
                                    dummy = f.readline()

                            # search the pattern
                            while True:
                                logging.debug("Search the pattern")
                                line = f.readline()
                                if line:
                                    last_number += 1
                                    logging.debug("Search the pattern from whole line")
                                    if search_type == "regexp":
                                        matched_str = re.search(search_str, line)
                                        if matched_str:
                                            # Consider the same "patternsearch" as duplicate
                                            matched_lines.append(dict(matched_contents=matched_str.group(0)))
                                    elif search_type == "starts with":
                                        if line.startswith(search_str):
                                            matched_lines.append(dict(matched_contents=search_str))
                                    elif search_type == "ends with":
                                        if line.endswith(search_str):
                                            matched_lines.append(dict(matched_contents=search_str))
                                    elif search_type == "substring":
                                        if line.find(search_str) >= 0:
                                            matched_lines.append(dict(matched_contents=search_str))
                                    elif search_type == "exactly":
                                        if line == search_str:
                                            matched_lines.append(dict(matched_contents=search_str))
                                else:
                                    break

                            # Save the last_number for every logicalname & logfilename to list variable: last_line_list
                            # Only when read_type is "incremental"
                            if read_type == "incremental":
                                logging.debug("Save the last_number for every logicalname & logfilename to list: \n")
                                existing_YN = False
                                # Check if the last_number is already exising for logicalname & logfilename
                                for item in last_line_list:
                                    if item["logicalname"] == logicalname and item["logfilename"] == logfilename:
                                        # noinspection PyPep8Naming
                                        existing_YN = True
                                        item["last_number"] = last_number

                                if not existing_YN:
                                    # Append it as new one
                                    last_line_list.append(
                                        dict(logicalname=logicalname, logfilename=logfilename, last_number=last_number))
                                    existing_YN = True

                                logging.debug(last_line_list)

                        # print("Matched lines for %s are:" % mylist_logfile_entry["logfilename"])

                        # Process for "deduplicate"
                        matched_lines_new = []
                        if mylist_logfile_entry["deduplicate"].lower() == "y":
                            logging.debug("deduplicate is: %s" % mylist_logfile_entry["deduplicate"])
                            for j in range(len(matched_lines)):

                                line_content = matched_lines[j]["matched_contents"]  # line's content
                                found = False
                                for k in range(len(matched_lines_new)):
                                    if matched_lines_new[k]["matched_contents"] == line_content:  # Exact match
                                        found = True
                                        if "num" in matched_lines_new[k].keys():
                                            matched_lines_new[k]["num"] += 1  # if line exists
                                        else:
                                            matched_lines_new[k]["num"] = 1  # if line is new
                                if not found:  # If not found, will copy to
                                    matched_lines_new.append(dict(matched_contents=line_content, num=1))

                        else:
                            matched_lines_new = copy.deepcopy(matched_lines)
                            for j in range(len(matched_lines_new)):
                                matched_lines_new[j]["num"] = 1  # if line is new

                                # new data: matched_lines_new is already gererated instead matched_lines

                                #            if len(matched_lines_new) > 0:
                                #                print(len(matched_lines_new))
                                #                print("Matched lines are:")
                                #                print(matched_lines_new)
                                #            else:
                                #                logging.info("There is not any/new matched message from logfile/s")
                                #                print("There is not any/new matched message from logfile/s")

                        # Update fields value if required
                        for j in range(len(matched_lines_new)):

                            logging.debug("Update fields value if required")
                            out_item_temp = copy.deepcopy(OUT_ITEM_SAMPLE)
                            for k in out_item_temp.keys():
                                #            print(mylist_logfile[i])
                                if mylist_logfile_entry.get(k):
                                    #
                                    out_item_temp[k] = mylist_logfile_entry[k]

                            # Update the output contents if there is relevant item from parameter file
                            # for key in ["eventtype", "logfilename", "logfield1", "logfield2" ]:
                            #     out_item_temp[key] = mylist_logfile_entry[key]
                            out_item_temp["logeventtype"] = mylist_logfile_entry["eventtype"]
                            #
                            # Update the output contents with combination
                            out_item_temp["resource"] = "%s:%s:%s:%s:%s" % (
                                mylist_logfile_entry.get("instance", ""),
                                mylist_logfile_entry.get("logfilename", ""),
                                mylist_logfile_entry.get("eventtype", ""),
                                mylist_logfile_entry.get("logfield1", ""),
                                mylist_logfile_entry.get("logfield2", "")
                            )

                            out_item_temp["responsible"] = mylist_logfile_entry.get("responsible", "")

                            out_item_temp["actualnumberofhits"] = matched_lines_new[j].get("num",
                                                                                           0)  # Update the number of hits
                            out_item_temp["message"] = matched_lines_new[j].get("matched_contents", "")

                            # Update the message with line's content

                            # Set default rc & rcdesc
                            if out_item_temp["rc"] == '':
                                # set default
                                RC = 0
                                out_item_temp["rc"] = RC

                            # Write data to output file
                            write_data_outfile(out_item_temp)

                            out_item_temp.clear()  # Clear for next searching

                    # Update the last_number for every logicalname & logfilename to file: \
                    # LAST_CHECKED_LINE from list variable: last_line_list
                    logging.debug(
                        "Update the last_number for every logicalname & logfilename to file: %s" % LAST_CHECKED_LINE)

                    # Merge the contents between LAST_CHECKED_LINE and last_line_list to "-bak" file
                    # Updated only when for "incremental"
                    if read_type == "incremental":
                        with open(LAST_CHECKED_LINE, 'r') as f1, open("%s-bak" % LAST_CHECKED_LINE, 'w') as f2:
                            # If LAST_CHECKED_LINE has, but last_line_list has not, copy it to "-bak" file;
                            # Both LAST_CHECKED_LINE and last_line_list have, write it with last_line_list value;
                            for line in f1:
                                l_logicalname, l_logfilename, l_number = line.split()
                                existing_yn = False
                                for item in last_line_list:
                                    logicalname = item["logicalname"]
                                    logfilename = item["logfilename"]
                                    number = item["last_number"]
                                    if logicalname == l_logicalname and logfilename == l_logfilename:
                                        existing_yn = True
                                        f2.write("%s  %s  %d\n" % (logicalname, logfilename, number))
                                        break
                                if not existing_yn:
                                    f2.write(line)

                        # move the backup file to it
                        os.remove(LAST_CHECKED_LINE)
                        os.rename("%s-bak" % LAST_CHECKED_LINE, LAST_CHECKED_LINE)

                        # copy all contents to the backup file
                        with open(LAST_CHECKED_LINE, 'r') as f1, open("%s-bak" % LAST_CHECKED_LINE, 'w') as f2:
                            for line in f1:
                                f2.write(line)

                        # append the some data to the backup file
                        for item in last_line_list:
                            # If last_line_list has, but LAST_CHECKED_LINE has not,
                            # write it to "-bak" file with last_line_list values
                            logicalname = item["logicalname"]
                            logfilename = item["logfilename"]
                            number = item["last_number"]
                            with open(LAST_CHECKED_LINE, 'r') as f1, open("%s-bak" % LAST_CHECKED_LINE, 'a') as f2:
                                existing_yn = False
                                for line in f1:
                                    l_logicalname, l_logfilename, l_number = line.split()
                                    if logicalname == l_logicalname and logfilename == l_logfilename:
                                        existing_yn = True
                                        break
                                if not existing_yn:
                                    f2.write("%s  %s  %d\n" % (logicalname, logfilename, number))

                        os.remove(LAST_CHECKED_LINE)
                        os.rename("%s-bak" % LAST_CHECKED_LINE, LAST_CHECKED_LINE)

                        logging.debug("After updated, the contents are: ")
                        # logging.debug(os.system('cat LAST_CHECKED_LINE'))

                # Sleep to next interval
                time.sleep(SCRIPT_INTERVAL_RUN)
            elif script_mode == "read":

                # exit if another deamon/process is already running for 'run'
                names = ["LogfileMonitor -m read", "LogfileMonitor.py -m read"]
                for name in names:
                    if sys.platform == "linux":
                        if process_already_running(name):
                            logging.error("The process(%s) is already running, Please verify with 'ps -f' command!!!" % name)
                            RC = 7
                            raise SystemExit(RC)
                    else:
                        logging.error("It is not supported to check the running process on other platforms")
                        RC = 100
                        raise SystemExit(RC)

                # Generate the output format of READ mode
                output_string_format = READ_OUTPUT_FORMAT["separator"].join(READ_OUTPUT_FORMAT["fields"].split())
                logging.debug("The output string format is:\n%s" % output_string_format)

                # Check if there is any data from RUN
                if not os.path.isfile(OUT_FILE):
                    RC = 2
                    raise SystemExit(RC)

                out_data = get_from_yaml(OUT_FILE)  # Get data from sample file
                # Check if the YAML file is valid (list data type)
                valid_yaml_format(OUT_FILE, out_data, "list")

                try:
                    with open(OUT_FILE) as f:
                        out_data = yaml.load(f)

                        if out_data:
                            # If there is any data read into
                            OUTPUT_ITEMS = []
                            updated_yn = False
                            script_exit = False
                            str1 = ""
                            for item in out_data:
                                # Check if the all the fields are can be read out
                                keys = list(item.keys())
                                # run a loop with: if is it un-read, append the item to OUTPUT_ITEMS
                                if item["readout"].lower() == "n":
                                    for item_key in list(READ_OUTPUT_FORMAT["fields"].split()):
                                        # If all the required are defined or not
                                        if item_key not in keys:
                                            RC = 9
                                            script_exit = True
                                            str1 += "%s@%s;" % (item_key, item["timestamp"])
                                    if script_exit:
                                        logging.error("Fields are missing from : %s" % str1)
                                        # print("Script exit with error: %s" % str1)
                                        raise SystemExit(RC)
                                    else:
                                        # append it
                                        item["readout"] = "Y"
                                        OUTPUT_ITEMS.append(item)
                                        updated_yn = True

                            logging.debug("The un-read items are: ")
                            logging.debug(OUTPUT_ITEMS)

                            if updated_yn:
                                # Write the 'READ' data to OUT_FILE instead
                                # result = yaml.dump(out_data, default_flow_style=False)
                                result = yaml.dump(OUTPUT_ITEMS, default_flow_style=False)

                                # Writ the data back to file: OUT_FILE
                                with open("%s-bak" % OUT_FILE, 'w') as f2:
                                    f2.write(result)

                                # Do not check if OUT_FILE was updated by RUN mode in above duration
                                os.remove(OUT_FILE)
                                os.rename("%s-bak" % OUT_FILE, OUT_FILE)

                            # Generate Standard Output for OUTPUT_ITEMS with OUT_FILE format
                            if OUTPUT_ITEMS:

                                separator = READ_OUTPUT_FORMAT["separator"]
                                fields = READ_OUTPUT_FORMAT["fields"]

                                for item in OUTPUT_ITEMS:
                                    logging.debug("The item is: ")
                                    logging.debug(item)
                                    # return the item contents with output_string_format format
                                    output_string = separator
                                    for key in fields.split():
                                        if str(item.get(key)):
                                            output_string = "%s%s%s" % (output_string, separator, item[key])
                                        else:
                                            logging.error(
                                                "The key of %s maybe wrong to defined in file: %s" % (key, OUT_FILE))
                                            output_string = "%s%sNULL" % (output_string, separator)

                                    output_string = output_string.strip(separator)
                                    print(output_string)

                        else:
                            logging.warning("There is not any data for input from file: %s" % OUT_FILE)
                except IOError:
                    logging.error("The file is not existing: %s" % OUT_FILE)
                    RC = 2
                    raise SystemExit(RC)
                break
        # Exit with RC
        # raise SystemExit(RC)
    except SystemExit as error_code:
        # Print desc for RC
        if str(error_code) != "0":
            found_yn = False
            for item in RETURN_CODE_DESC:
                if item["rc"] == str(error_code):
                    logging.info(item["desc"])
                    found_yn = True
                    break
            if not found_yn:
                item["desc"] = "Description is not defined"

            # Send the same output to stdout for errors
            logging.error("%s;;%s" % (item.get("rc"), item.get("desc")))
            print("%s;;%s" % (item.get("rc"), item.get("desc")))

        sys.exit(error_code)
        # return error_code
    except Exception as e:
        logging.error(e)
        print("99;;Undefined error message in script")
        sys.exit(99)
    finally:
        pass
    #     # Clear temparory files
    # End of Main


if __name__ == "__main__":
    main()
