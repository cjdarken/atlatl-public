simple_test: simple_copy test
cnn_test: cnn_copy test
simple_copy:
	cp simple_test.py create_test.py
cnn_copy:
	cp cnn_test.py create_test.py
test :
	python create_test.py
	mv mymodel testdir
	cd testdir; python read_test.py;
clean : 
	rm -rf __pycache__ mymodel model.pt testdir/mymodel testdir/__pycache__ create_test.py
