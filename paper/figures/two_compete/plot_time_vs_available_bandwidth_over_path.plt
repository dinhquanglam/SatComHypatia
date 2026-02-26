reset
set terminal pdfcairo size 6in,3in font ",10"
set output "plot_time_vs_available_bandwidth_over_path.pdf"
set title "Skipped: missing two_compete dataset"
set xlabel "time (s)"
set ylabel "value"
plot 0 title "" w points
set output
