
app: advisor_matching.py advisor_matching.spec
	pyinstaller --onefile --windowed advisor_matching.py

clean:
	rm -rf build/ dist/
