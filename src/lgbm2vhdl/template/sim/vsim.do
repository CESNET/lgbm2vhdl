vcom -2008 testbench.vhd

vsim -voptargs=+acc work.testbench
#restart -f 

do wave.do

run -all

exit