# vim: shiftwidth=8 tabstop=8 noexpandtab textwidth=0

#

#VERSION=$(shell  ./Version.py version)
#APP_VER=$(shell  ./Version.py AppVerName)
#AppVerName="CrossMgr 3.1.64-private"

VER=$(shell  python ./version.py)

EXES = usbtestnet.exe pinglog.exe

all: ${EXES} belcarra_usbtestkit-${VER}.zip

%.exe : %.py
	time -p python -m nuitka \
		--onefile \
    		--windows-icon-from-ico=./usbtest.png \
		$<
	belcarra-signtool $*.exe

test:
	@echo VER: ${VER}
	@echo EXES: ${EXES}

belcarra_usbtestkit-${VER}.zip: ${EXES}
	zip belcarra_usbtestkit-${VER}.zip $^

clean:
	-rm -rf *build *dist

really-clean: clean
	-rm -rf *.exe 
