project_name ?= picox-8
target ?= xc9572xl-10-VQ44


# alternative speed, density
optimize ?= speed

all: lso synthesis ngdbuild cpldfit tsim jedec

lso:
	echo "work" > ${project_name}.lso

# Synthesis
synthesis:  ${project_name}.xst ${project_name}.lso
	if [ ! -d tmp ] ; then mkdir tmp ; fi
	xst -ifn ./${project_name}.xst -intstyle xflow -ofn ./${project_name}.syr


ngdbuild: ${project_name}.ucf ${project_name}.ngc 
	ngdbuild -dd _ngo -p ${target} -uc ${project_name}.ucf ${project_name}.ngc  ${project_name}.ngd


# Fit the selected device and generate reports
cpldfit:  ${project_name}.ngd
	cpldfit -p ${target} \
	    -ofmt vhdl \
	    -optimize ${optimize} \
	    -loc on \
	    -slew slow \
	    -init low \
	    -inputs 22 \
	    -pterms 24 \
	    -power std \
	    -exhaust ${project_name}.ngd

# Run the TA engine and generate reports
tsim:   
	tsim ${project_name} ${project_name}.nga
	taengine -f ${project_name} -detail

# Generate the JEDEC file for programming
jedec: 
	hprep6  -s IEEE1149 -n ${project_name} -i ${project_name}
	mv ${project_name}.jed ${project_name}_${target}.jed

# dump a verilog netlist
netgen:
	netgen -w -ofmt verilog  -aka ${project_name}.ngd



clean:
	$(RM) -fr _ngo/ \
		_xmsgs/ \
		$(project_name).bld \
		$(project_name).gyd \
		$(project_name).lso \
		$(project_name).mfd \
		$(project_name).nga \
		$(project_name).ngd \
		$(project_name).nlf \
		$(project_name).pad \
		$(project_name).pnx \
		$(project_name).rpt \
		$(project_name).syr \
		$(project_name).tim \
		$(project_name).vm6 \
		$(project_name).xml \
		$(project_name)_build.xml \
		$(project_name)_ngdbuild.xrpt \
		$(project_name)_pad.csv \
		$(project_name)_xc9572xl-5-VQ64.jed \
		$(project_name)_xst.xrpt \
		tmperr.err \
		PicoX8.lso \
		$(project_name).ngc \
		$(project_name).ngr \
		tmperr.err \
		xlnx_auto_0_xdb/ \
		xst/ \
		tmp/ \
		*~
