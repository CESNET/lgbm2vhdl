onerror {resume}
quietly WaveActivateNextPane {} 0
add wave -noupdate /testbench/clk
add wave -noupdate /testbench/rst
add wave -noupdate /testbench/start
add wave -noupdate /testbench/finish
add wave -noupdate /testbench/mi_in_wr
add wave -noupdate /testbench/mi_in_waddr
add wave -noupdate /testbench/mi_in_wdata
add wave -noupdate /testbench/mi_out_raddr
add wave -noupdate /testbench/mi_out_rdata
add wave -noupdate -divider {Input Memory}
add wave -noupdate /testbench/uut/MI_IN_U/CLK
add wave -noupdate /testbench/uut/MI_IN_U/WR
add wave -noupdate /testbench/uut/MI_IN_U/WADDR
add wave -noupdate /testbench/uut/MI_IN_U/WDATA
add wave -noupdate /testbench/uut/MI_IN_U/RADDR
add wave -noupdate /testbench/uut/MI_IN_U/RDATA
add wave -noupdate /testbench/uut/MI_IN_U/RAM
add wave -noupdate -divider {Feature FSM}
add wave -noupdate /testbench/uut/FSM_FEATURE_U/CLK
add wave -noupdate /testbench/uut/FSM_FEATURE_U/RST
add wave -noupdate /testbench/uut/FSM_FEATURE_U/START
add wave -noupdate /testbench/uut/FSM_FEATURE_U/CNT_OVER
add wave -noupdate /testbench/uut/FSM_FEATURE_U/CNT_INIT
add wave -noupdate /testbench/uut/FSM_FEATURE_U/CNT_EN
add wave -noupdate /testbench/uut/FSM_FEATURE_U/FINISH
add wave -noupdate /testbench/uut/FSM_FEATURE_U/present_state
add wave -noupdate /testbench/uut/FSM_FEATURE_U/next_state
add wave -noupdate -divider {Input Registers}
add wave -noupdate /testbench/uut/cnt_feature
add wave -noupdate /testbench/uut/reg_feature_en
add wave -noupdate /testbench/uut/reg_feature
add wave -noupdate -divider {LGBM Model}
add wave -noupdate /testbench/uut/LGBT_U/FEATURES_EN
add wave -noupdate /testbench/uut/LGBT_U/FEATURES
add wave -noupdate /testbench/uut/LGBT_U/OUTPUT_EN
add wave -noupdate /testbench/uut/LGBT_U/CLASS
add wave -noupdate -divider {Output Registers}
add wave -noupdate /testbench/uut/class_en
add wave -noupdate /testbench/uut/reg_class
add wave -noupdate -divider {Output Memory}
add wave -noupdate /testbench/uut/MI_OUT_U/CLK
add wave -noupdate /testbench/uut/MI_OUT_U/WR
add wave -noupdate /testbench/uut/MI_OUT_U/WADDR
add wave -noupdate /testbench/uut/MI_OUT_U/WDATA
add wave -noupdate /testbench/uut/MI_OUT_U/RADDR
add wave -noupdate /testbench/uut/MI_OUT_U/RDATA
add wave -noupdate /testbench/uut/MI_OUT_U/RAM
TreeUpdate [SetDefaultTree]
WaveRestoreCursors {{Cursor 1} {4135 ns} 0}
quietly wave cursor active 1
configure wave -namecolwidth 279
configure wave -valuecolwidth 126
configure wave -justifyvalue left
configure wave -signalnamewidth 0
configure wave -snapdistance 10
configure wave -datasetprefix 0
configure wave -rowmargin 4
configure wave -childrowmargin 2
configure wave -gridoffset 0
configure wave -gridperiod 1
configure wave -griddelta 40
configure wave -timeline 0
configure wave -timelineunits ns
update
WaveRestoreZoom {0 ns} {5313 ns}
