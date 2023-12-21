# Load Quartus Prime Tcl Project package
package require ::quartus::project

# Only open if not already open
if {[project_exists design]} {
	project_open -revision design design
} else {
	project_new -revision design design
}

project_clean

project_open -revision design design

# Make assignments
set_global_assignment -name TOP_LEVEL_ENTITY WRAPPER

set_global_assignment -name ORIGINAL_QUARTUS_VERSION 22.4.0
set_global_assignment -name PROJECT_CREATION_TIME_DATE "10:45:07  AUGUST 27, 2023"
set_global_assignment -name LAST_QUARTUS_VERSION "22.4.0 Pro Edition"
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name MIN_CORE_JUNCTION_TEMP 0
set_global_assignment -name MAX_CORE_JUNCTION_TEMP 100
set_global_assignment -name DEVICE AGFB014R24C2E1V
set_global_assignment -name FAMILY Agilex
set_global_assignment -name ERROR_CHECK_FREQUENCY_DIVISOR 256
set_global_assignment -name PWRMGT_VOLTAGE_OUTPUT_FORMAT "LINEAR FORMAT"
set_global_assignment -name PWRMGT_LINEAR_FORMAT_N "-12"
set_global_assignment -name SDC_FILE design.sdc
set_global_assignment -name VHDL_INPUT_VERSION VHDL_2008 

# Add all source files
set f [open "files.txt"]
set lines [split [read $f] "\n"]
close $f;
foreach line $lines {
    # puts $line
    set_global_assignment -name VHDL_FILE $line
}

# Commit assignments
export_assignments

# Close project
project_close
