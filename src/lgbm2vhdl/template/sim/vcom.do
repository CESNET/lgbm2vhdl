if {[file exist work]} {
    vdel -all
    puts "Work Library Deleted"
}
vlib work

set f [open files.txt]
set lines [split [read $f] "\n"]
close $f;
foreach line $lines {
    vcom -2008 $line
}

exit