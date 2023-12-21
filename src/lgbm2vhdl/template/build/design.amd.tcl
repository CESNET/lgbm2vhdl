# design.tcl
#
create_project project output_files -force -part xc7z020clg484-1

# Add all source files
set f [open "files.txt"]
set lines [split [read $f] "\n"]
close $f;
foreach line $lines {
    # puts $line
    add_files $line
    set_property FILE_TYPE {VHDL 2008} [get_files $line]
}

set_property top WRAPPER [current_fileset]

# Read Constraints
read_xdc design.xdc

# Launch Synthesis
launch_runs synth_1
wait_on_run synth_1

open_run synth_1 -name netlist_1
# Generate a timing and power reports and write to disk
report_timing_summary -delay_type max -report_unconstrained -check_timing_verbose -max_paths 10 -input_pins -file vivado_syn_timing.rpt
report_utilization -file vivado_syn_utilization.rpt

# Launch Implementation
launch_runs impl_1
wait_on_run impl_1 

# Generate a timing and power reports and write to disk
# comment out the open_run for batch mode
open_run impl_1
report_timing_summary -delay_type min_max -report_unconstrained -check_timing_verbose -max_paths 10 -input_pins -file vivado_imp_timing.rpt
report_utilization -file vivado_imp_utilization.rpt
