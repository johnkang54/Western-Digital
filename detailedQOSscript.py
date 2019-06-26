import csv
import sys
import re

with open(sys.argv[1]) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0

    #containers
    dictionary_of_QOS = {}
    dictionary_of_FFLBA_to_cmdindex = {}
    dictionary_of_VBA_to_cmdindex = {}
    result_dictionary_of_QOS = []

    current_cmd_index_for_vba = ""

    cmd_idx_syntax = ["cmd idx", "cmdidx"]
    
    ############# reading from csv #####################
    for row in csv_reader:
        # print line_count 
        
        if line_count == 0:
            print 'Columns:', ", ".join(row)

        line_count += 1

        if "Process Begin" in row[2]: #no parameter
            continue

        opcode = row[4][-2:]
        if ("Host command reception by HNVMe" in row[3] and opcode == "02"):
            cmd_index = row[4][12:15]
            dictionary_of_QOS[cmd_index] = [row] #cmd index and row
            continue
        
        elif "HNVMe descriptor completion" in row[3]:
            cmd_index = row[4][12:15]
            if cmd_index in dictionary_of_QOS:
                dictionary_of_QOS[cmd_index].append(row)
                continue
            

        elif "Command Comletion" in row[3]:
            cmd_index = row[4][11:14]
            if cmd_index in dictionary_of_QOS:
                dictionary_of_QOS[cmd_index].append(row)
                result_dictionary_of_QOS.append((cmd_index,dictionary_of_QOS[cmd_index]))
                dictionary_of_QOS.pop(cmd_index)#pop after so i can still find the cmd index
                continue

        #looking for cmd idx in the name
        for syntax in cmd_idx_syntax:
            if syntax in row[3].lower():
                array_of_parameters_name = row[3][row[3].find("(")+1:row[3].find(")")].lower().split("|")

                array_of_parameters_parameter = row[4].split("|")
                array_of_parameters_parameter = [parameter.strip(' ') for parameter in array_of_parameters_parameter]
                
                #gives index of where the cmd index is to use for the second list
                cmd_index = [indices for indices, param in enumerate(array_of_parameters_name) if syntax in param]
                cmd_index = cmd_index[0]
                cmd_index = array_of_parameters_parameter[cmd_index][-3:] #truncate
                
                #to link vba to the cmd idx
                if("FTL: PSR: host read (JBID-|jbFmu|secOffset|secLength|streamStat|cmdIdx|cmdOset)" in row[3]):
                    current_cmd_index_for_vba = cmd_index

                if(cmd_index in dictionary_of_QOS):
                    #linked between FFLBA and cmd idx
                    if "FTL: HRF: Start Handle Flow" in row[3]:
                        fflba = row[4][:10]
                        dictionary_of_FFLBA_to_cmdindex[fflba] = cmd_index
                        dictionary_of_QOS[cmd_index].append(row)
                        break

                    
                    

                    dictionary_of_QOS[cmd_index].append(row)
                #done
                break
        
        #looking for FFLBA in the name
        if "FFLBA" in row[3]:
            array_of_parameters_name = row[3][row[3].find("(")+1:row[3].find(")")].lower().split("|")
            array_of_parameters_parameter = row[4].split("|")
            array_of_parameters_parameter = [parameter.strip(' ') for parameter in array_of_parameters_parameter]
            fflba = [indices for indices, param in enumerate(array_of_parameters_name) if "fflba" in param]
            #picks the first instance of the keyword
            fflba_index = fflba[0]
            fflba = array_of_parameters_parameter[fflba_index]

            if(fflba in dictionary_of_FFLBA_to_cmdindex):
                if(dictionary_of_FFLBA_to_cmdindex[fflba] in dictionary_of_QOS):
                    cmd_index = dictionary_of_FFLBA_to_cmdindex[fflba]
                    dictionary_of_QOS[cmd_index].append(row)
                    continue

        lower_row3 = row[3].lower()
        if "vba" in lower_row3:
            array_of_parameters_name = row[3][row[3].find("(")+1:row[3].find(")")].lower().split("|")
            array_of_parameters_parameter = row[4].split("|")
            array_of_parameters_parameter = [parameter.strip(' ') for parameter in array_of_parameters_parameter]
            vba = [indices for indices, param in enumerate(array_of_parameters_name) if "vba" in param]
            #picks the first instance of the keyword
            vba_index = vba[0]
            vba = array_of_parameters_parameter[vba_index]

            #linking VBA to current cmdidx
            if ("FTL: PSR: host read VBA (VBA-)" in row[3]):
                dictionary_of_VBA_to_cmdindex[vba] = current_cmd_index_for_vba

            if(vba in dictionary_of_VBA_to_cmdindex):
                if(dictionary_of_VBA_to_cmdindex[vba] in dictionary_of_QOS):
                    cmd_index = dictionary_of_VBA_to_cmdindex[vba]
                    dictionary_of_QOS[cmd_index].append(row)
                    continue

    
    print "Number of Events Processed:", line_count - 1

    ############## writes to new csv file (need to change file name each time, cant override#######
    with open(sys.argv[2], 'wb') as csvfile:
        iops_writer = csv.writer(csvfile, delimiter=' ',
                            quotechar=' ', quoting=csv.QUOTE_MINIMAL)
        for first, second in result_dictionary_of_QOS:
            for events in second:
                iops_writer.writerow([events[0], ",", events[1],",", events[2],",", events[3],",", events[4],",", events[5],",", events[6]])

