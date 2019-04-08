#!/usr/bin/env python3
# -*- coding:utf8 -*-
"""
###################################################################
# changes :                                                       #
# 20190301-XJS : Initial   supports Python 3.5                    #
# 20190408-XJS :           supports both RUN and READ mode        #
###################################################################
# Search the pattern from the monitored log file/s, and generate the output with defined format

"""
import copy
import logging
import os
import re
import sys
import time

import yaml

SCRIPT_NAME = os.path.basename(__file__)

d = os.path.dirname(__file__)

# set default values for RUN mode
PARAM_FILE, OUT_FILE, RC_FILE = \
    os.path.join(d, "LogfileMonitorParam.yml"), \
    os.path.join(d, "LogfileMonitorOut.yml"), \
    os.path.join(d, "ReturnedCode.yml")

# define the output format
OUT_SAMPLE = os.path.join(d, "LogfileMonitorOut.sample")

# Monitor logfile in 1 minutes interval
SCRIPT_INTERVAL_RUN = 1

# set default values for READ mode
FORMAT_FILE, OUT_FILE, RC_FILE = \
    os.path.join(d, "LogfileMonitorReadFormat.yml"), \
    os.path.join(d, "LogfileMonitorOut.yml"), \
    os.path.join(d, "ReturnedCode.yml")

# Monitor logfile in 1 minutes interval
SCRIPT_INTERVAL_READ = 1

###
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
    print("          %s -m RUN [-p <Parameter file>] [-o <Output file>]" % SCRIPT_NAME)
    print("      or: %s -m READ [-f <Format file>] [-o <Output file>]" % SCRIPT_NAME)
    print("")
    print("while '-m RUN':")
    print("    -p <Parameter file>  The parameter file, default is LogfileMonitorPara.yml")
    print("    -o <Output file>  The output file, default is LogfileMonitorOut.yml")
    print("")
    print("while '-m READ':")
    print("    -f <Format file>  The config file for output format, default is LogfileMonitorReadFormat.yml")
    print("    -o <Output file>  The output file of 'RUN' mode, default is LogfileMonitorOut.yml")

    sys.exit(1)


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
        else:
            usage()
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
    logging.info("Capture the data of: (%s) to a variable" % file)
    try:
        with open(file) as f:
            filed = yaml.load(f)
    except IOError:
        logging.error("RC=1, File access error: %s" % file)

        OUT_ITEM_SAMPLE["rc"] = "1"
        write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file
        OUT_ITEM_SAMPLE["rc"] = ""

    except:
        logging.error("RC=99, File might not exactly apply YAML format: %s" % file)
        logging.error(str(Exception))

        OUT_ITEM_SAMPLE["rc"] = "99"
        write_data_outfile(OUT_ITEM_SAMPLE)  # Append the data into output file
        OUT_ITEM_SAMPLE["rc"] = ""

    return filed


def valid_param_data(data, mylist_out):
    """
    Validate the parameters defined in Parameters file
    :param mylist_out:
    :param data:
    :return: update the contents of variable of mylist_out
    """

    for i in range(len(data)):
        item = copy.deepcopy(data[i])

        # Check the required parameters
        required_list = ["logicalname", "logfilename"]
        logging.info("TBD: will verify the list of required parameters:\n %s" % required_list)
        for k in required_list:
            if not item.get(k) or not item[k]:
                # Not configured or NULL
                print("Parameter is missing for: %s" % k)

                # return error
                print("Return error")

        logging.info("TBD: will validate the parameters of:\n %s" % data)
        pass
        # e.g to fill the returned code to 3 with "invalid parameters" into mylist_out
        mylist_out[0]["rc"] = "3"

    return mylist_out


def trans_pattern_logfile(mylist_1):
    """
    Translate the search pattern to the exact logfilename/s from the regexp if have
    :param mylist_1:
    :return: mylist_2
    """
    global OUT_ITEM_SAMPLE

    logging.debug("To be translated search pattern with regexp logfilenames:")
    for i in range(len(mylist_1)):
        logging.debug(mylist_1[i])
    mylist_2 = []

    for i in range(len(mylist_1)):
        match_yn = False
        # Save the item of pattern search for logfilename regexp
        item_logfilename = copy.deepcopy(mylist_1[i])

        # Get the filename and dir name
        logging.debug("logfilename regexp is: %s" % item_logfilename["logfilename"])

        file_exp = os.path.basename(item_logfilename["logfilename"])
        dir_exp = os.path.dirname(item_logfilename["logfilename"])

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
            logging.error("No matched logfile for: %s" % item_logfilename["logfilename"])
            # write the wrong message to output

            OUT_ITEM_SAMPLE = copy.deepcopy(item_logfilename)
            # set the return code for "NO MATCHED LOGFILE FOUND"
            OUT_ITEM_SAMPLE["rc"] = 21

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
    : Global: OUT_FILE, RC_FILE
    :return: Update OUT_FILE
    """

    global OUT_FILE, RC_FILE
    # Get rcdesc relies on rc from RC_FILE file
    mylist_rc = get_from_yaml(RC_FILE)

    return_code = str(out_item["rc"])  # while rc is interger data type

    if return_code:
        out_item["rcdesc"] = "RC is not defined"  # If it is missing in configuration

        for i in range(len(mylist_rc)):
            if return_code == mylist_rc[i]["rc"]:
                out_item["rcdesc"] = mylist_rc[i]["desc"]
                break

    # Set default values if missing
    if not out_item.get("timestamp"):
        out_item["timestamp"] = int(time.time())  # Set timestamp
    if not out_item.get("readout"):
        out_item["readout"] = "N"  # set it as default

    # Update the output contents if there is relevant item from parameter file
    if not out_item.get("logeventtype"):
        out_item["logeventtype"] = out_item["eventtype"]

    if not out_item.get("resource"):
        out_item["resource"] = "%s:%s:%s:%s" % \
                               (out_item["logfilename"], out_item["eventtype"],
                                out_item["logfield1"], out_item["logfield2"])

    # if there is not any matched contents
    if not out_item.get("message"):
        out_item["message"] = out_item["matched_contents"] if out_item.get("matched_contents") else "NULL"

    if not out_item.get("actualnumberofhits"):
        out_item["actualnumberofhits"] = 0

    # Update the message with line's content

    # Append the new item into OUT_FILE
    out_data = [out_item]

    #    result = yaml.dump(out_data, encoding='utf-8', allow_unicode=True, default_flow_style=False)
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
    str1 = ""
    # The required parameters
    para = ["logfilename", "instance", "eventtype", "readtype", "rotation", "alarmonerror",
            "alarmonerrorsev", "deduplicate", "occurences", "responsible", "logfield1", "logfield2"]
    str1 = check_required_parameters(mydict, para)
    if str1:
        str1 = "Parameters are missing: %s" % str1

    # The Optional parameters
    para2 = ["clearmatch", "sev1match", "sev2match", "sev3match",
             "clearmap", "sev1map", "sev2map", "sev3map", "patternsearchtype"]

    str2 = check_valid_parameters(mydict, para + para2)
    if str2:
        str2 = "Parameters are invalid: %s" % str2
    str1 += " && %s" % str2

    # The valid contents for specific fields
    pass

    return str1


def main():
    global CONFIG_FILE, PARAM_FILE, OUT_FILE, OUT_SAMPLE
    global OUT_ITEM_SAMPLE, SCRIPT_INTERVAL_RUN

    global FORMAT_FILE, SCRIPT_INTERVAL_READ

    OUT_ITEM_SAMPLE = {}

    # create the file to save the number of last checked line for every logfile
    # noinspection PyPep8Naming
    PROCESS_ID = os.getpid()  # Get process id
    # noinspection PyPep8Naming
    LAST_CHECKED_LINE = "%s.loc" % PROCESS_ID

    with open(LAST_CHECKED_LINE, 'w') as f:
        f.write("logicalname     logfilename      0\n")

    try:
        while True:
            # Get args
            argv = sys.argv
            logging.info(argv)
            mydict = get_argv_dict(argv)

            # Validate the imput parameters

            # Check the required parameter/s
            para = ["-m"]
            if check_required_parameters(mydict, para):
                logging.error("The required parameter is missing: %s" % check_required_parameters(mydict, para))
                usage()

            # validate the value of "-m", should be RUN/READ
            script_mode = mydict.get("-m").lower()
            if script_mode not in ["run", "read"]:
                logging.error("The value of '- m' is not valid: %s" % script_mode)
                # Write the wrong message to output with rc & rcdesc
                pass

                usage()

            # Check the optional parameter/s
            if script_mode == "run":
                para = ["script", "-m", "-p", "-o", "-h"]
            else:
                para = ["script", "-m", "-f", "-o", "-h"]

            if check_valid_parameters(mydict, para):
                logging.error("The parameter %s is/are not supported!!!" % check_valid_parameters(mydict, para))
                # Write the wrong message to output with rc & rcdesc
                pass

                usage()

            if script_mode == "run":
                # with RUN mode
                logging.info("file is:%s" % PARAM_FILE)

                if mydict.get("-c"):
                    CONFIG_FILE = mydict["-c"]
                if mydict.get("-p"):
                    PARAM_FILE = mydict["-p"]
                if mydict.get("-o"):
                    OUT_FILE = mydict["-o"]

                logging.info(PARAM_FILE)

                out_data = get_from_yaml(OUT_SAMPLE)  # Get data from sample file

                # Clear the data, and only keep the keys and default values, and save it as output sample data
                for k in out_data[0].keys():
                    if k not in ["actualnumberofhits", "maxnumberofhits", "ttl"]:
                        OUT_ITEM_SAMPLE[k] = ""
                    else:
                        # Set 0 for Interger type data
                        OUT_ITEM_SAMPLE[k] = 0

                # Get parameters from file
                mylist_param = get_from_yaml(PARAM_FILE)
                logging.debug("data for parameter file:\n %s" % mylist_param)

                # Validate the parameters of every item in config file
                for i in mylist_param:
                    if valid_para_config_file(i):
                        # If there is any invalid parameters include, or any invalid contents for any parameter
                        #print(valid_para_config_file(i))
                        pass

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
                    print("There is not any exactly match logfilename.")
                else:
                    logging.debug("All the search patterns with exact logfilename:")
                    for i in range(len(mylist_logfile)):
                        logging.debug(mylist_logfile[i])

                """
                ###
                # Search pattern in the specific logfile
                # Every item should like as following:
                # {'alarmonmatch': 'Y', 'responsible': 'Support Application 001', 'occurence': '1', \
                # 'eventtype': 'InitializationError', 'logicalname': 'http-server-log', 'readtype': 'Incremental', \
                # 'logfilename': '/tmp/http8.log', 'deduplicate': 'N', 'clearmatch': 'ABCRunning', 'instance': 'http', \
                # 'patternsearch': 'ErrorABC', 'rotation': 'N', 'logfield2': 'fieldx2', \
                # 'matchtype': 'substring', 'logfield1': 'fieldx1', 'sevrity': 'sev1'}
                #
                # Useful keys for searching are:
                #     logfilename, patternsearch, patternsearchtype ???
                # also depends on:
                #     readtype: Full/Increment
                #
                # will search as well for:
                #      clearmatch
                # The match pattern will add into global variable:out_data (a list which contains dictionary type data)
                """
                last_line_list = []

                for i in range(len(mylist_logfile)):
                    # Process for every monitored logfile
                    mylist_logfile_entry = mylist_logfile[i]

                    logfilename = mylist_logfile_entry["logfilename"]  # exact logfile name with path
                    search_str = mylist_logfile_entry["patternsearch"]  # regural expression
                    read_type = mylist_logfile_entry["readtype"]  # Incremental/Full

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
                                logging.warning("There not so many fields defined in file(>=3): %s" % LAST_CHECKED_LINE)

                    # search the pattern in logfilename
                    logging.debug("Search the pattern in logfilename")

                    with open(logfilename, 'r') as f:
                        # skip to the last checked line for "readtype: Incremental"
                        logging.debug("Skip to the last checked line")
                        if read_type.lower() == "incremental":
                            for ii in range(0, last_number):
                                dummy = f.readline()

                        # search the pattern
                        while True:
                            logging.debug("Search the pattern")
                            line = f.readline()
                            if line:
                                last_number += 1
                                logging.debug("Search the pattern from whole line")
                                if re.search(search_str, line):
                                    """
                                    # matched_lines.append(dict(line = line.strip()))
                                    # Get the matched message instead of line. e.g
                                    # 2019-03-08 15:03:39,878 - ERROR - RC=99, File might not exactly apply YAML format: LogfileMonitorParam.yml
                                    # will get "RC=99, File might not exactly apply YAML format: LogfileMonitorParam.yml" with following:
                                    # matched_lines.append(dict(line=line.strip().split(" - ")[2]))
                                    """
                                    matched_lines.append(dict(matched_contents=line.strip("\n")))
                                    # print(line)
                            else:
                                break

                        # Save the last_number for every logicalname & logfilename to list variable: last_line_list
                        logging.debug("Save the last_number for every logicalname & logfilename to list: \n")
                        # noinspection PyPep8Naming
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
                            # noinspection PyPep8Naming
                            existing_YN = True

                        logging.debug(last_line_list)

                    # print("Matched lines for %s are:" % mylist_logfile_entry["logfilename"])
                    #            print(matched_lines)

                    # Process for "deduplicate"
                    logging.info("TBD for deduplicate: which conditions should be taken as duplicated ???")
                    """
                    So far, matched_contents is the whole line message captured from monitored logfiles, normally, 
                    it will not be duplicated.
                    """
                    matched_lines_new = []
                    if mylist_logfile_entry["deduplicate"].lower() == "y":
                        logging.debug("deduplicate is: %s" % mylist_logfile_entry["deduplicate"])
                        for j in range(len(matched_lines)):

                            line_content = matched_lines[j]["matched_contents"]  # line's content
                            found = False
                            for k in range(len(matched_lines_new)):
                                if matched_lines_new[k]["matched_contents"] == line_content:  # Exact match
                                    found = True
                                    if matched_lines_new[k].get("num"):
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
                        # # Update the output contents with combination
                        out_item_temp["resource"] = "%s:%s:%s:%s" % (
                            mylist_logfile_entry["logfilename"], mylist_logfile_entry["eventtype"],
                            mylist_logfile_entry["logfield1"], mylist_logfile_entry["logfield2"])

                        out_item_temp["actualnumberofhits"] = matched_lines_new[j]["num"] \
                            if matched_lines_new[j].get("num") else 0  # Update the number of hits
                        out_item_temp["message"] = matched_lines_new[j]["matched_contents"] \
                            if matched_lines_new[j].get("matched_contents") else ""
                        # Update the message with line's content

                        # Set default rc & rcdesc
                        if out_item_temp["rc"] == '':
                            # set default
                            out_item_temp["rc"] = 0

                        # Write data to output file
                        write_data_outfile(out_item_temp)

                        out_item_temp.clear()  # Clear for next searching

                # Update the last_number for every logicalname & logfilename to file: \
                # LAST_CHECKED_LINE from list variable: last_line_list
                logging.debug(
                    "Update the last_number for every logicalname & logfilename to file: %s" % LAST_CHECKED_LINE)

                # Merge the contents between LAST_CHECKED_LINE and last_line_list to "-bak" file

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
                    # If last_line_list has, but LAST_CHECKED_LINE has not, write it to "-bak" file with last_line_list values
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
                time.sleep(SCRIPT_INTERVAL_RUN * 60)
                # print("RUN in next cycle...")
            else:
                # with READ mode
                # print("running with READ mode")
                if mydict.get("-o"):
                    OUT_FILE = mydict.get("-o")
                if mydict.get("-f"):
                    FORMAT_FILE = mydict.get("-f")

                out_format = get_from_yaml(FORMAT_FILE)  # Get data from format file

                # Valid the format
                para = ["separator", "fields"]
                # for key in keys:
                if check_required_parameters(out_format, para):
                    logging.error("The required parameter is missing: %s" % check_required_parameters(out_format, para))
                    print("The required parameter is missing: %s" % check_required_parameters(out_format, para))
                    exit(1)

                output_string_format = out_format["separator"].join(out_format["fields"].split())
                logging.debug("The output string format is:\n%s" % output_string_format)

                out_data = get_from_yaml(OUT_FILE)  # Get data from sample file

                if out_data:
                    # If there is any data read into
                    # noinspection PyPep8Naming
                    OUTPUT_ITEMS = []
                    updated_yn = False
                    for item in out_data:
                        # run a loop with: if is it un-read, append the item to OUTPUT_ITEMS
                        if item["readout"].lower() == "n":
                            # append it
                            OUTPUT_ITEMS.append(item)
                            # update t
                            item["readout"] = "Y"
                            updated_yn = True

                    logging.debug("The un-read items are: ")
                    logging.debug(OUTPUT_ITEMS)

                    if updated_yn:
                        result = yaml.dump(out_data, default_flow_style=False)

                        # Writ the data back to file: OUT_FILE
                        with open("%s-bak" % OUT_FILE, 'w') as f:
                            # write out_data to the -bak file
                            f.write(result)

                        # Do not check if OUT_FILE was updated by RUN mode in above duration
                        os.remove(OUT_FILE)
                        os.rename("%s-bak" % OUT_FILE, OUT_FILE)

                    out_data = []

                    # Generate Standard Output for OUTPUT_ITEMS with OUT_FILE format
                    if OUTPUT_ITEMS:
                        output_string_format = ""

                        out_format = get_from_yaml(FORMAT_FILE)  # Get data from sample file

                        separator = out_format["separator"]
                        fields = out_format["fields"]
                        # output_string_format = out_format["separator"].join(out_format["fields"].split())
                        # logging.debug("The output string format is:\n%s" % output_string_format)

                        for item in OUTPUT_ITEMS:
                            logging.debug("The item is: ")
                            logging.debug(item)
                            #                print(item)
                            # return the item contents with output_string_format format
                            output_string = separator
                            for key in fields.split():
                                if str(item.get(key)):
                                    output_string = "%s%s%s" % (output_string, separator, item[key])
                                else:
                                    logging.error(
                                        "The key of %s maybe wrong to defined in file: %s" % (key, OUT_FILE))
                                    print("ERROR The key of %s maybe wrong to defined in file: %s" % (key, OUT_FILE))
                                    output_string = "%s%sNULL" % (output_string, separator)

                            output_string = output_string.strip(separator)
                            print(output_string)
                else:
                    logging.debug("There is not any data for input from file: %s" % OUT_FILE)

                time.sleep(SCRIPT_INTERVAL_READ * 60)
    finally:
        # Clear temparory files
        if os.path.isfile(LAST_CHECKED_LINE):
            os.remove(LAST_CHECKED_LINE)
    # End of Main

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
