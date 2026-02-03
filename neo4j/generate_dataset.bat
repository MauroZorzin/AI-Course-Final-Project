@echo off
REM generate_dataset.bat
REM Generate a balanced question dataset

echo ============================================================
echo Question Dataset Generator
echo ============================================================
echo.

set OUTPUT_DIR=dataset
mkdir %OUTPUT_DIR% 2>nul

echo [1/4] Generating 1-hop questions (500)...
python neo4j_question_pipeline.py --random --length 1 --count 100 --output %OUTPUT_DIR%\questions_2hop.json
if %errorlevel% neq 0 goto error

echo.
echo [2/4] Generating 2-hop questions (300)...
python neo4j_question_pipeline.py --random --length 2 --count 100 --output %OUTPUT_DIR%\questions_3hop.json
if %errorlevel% neq 0 goto error

echo.
echo [3/4] Generating 3-hop questions (100)...
python neo4j_question_pipeline.py --random --length 3 --count 100 --output %OUTPUT_DIR%\questions_4hop.json
if %errorlevel% neq 0 goto error

echo.
echo [4/4] Merging datasets...
python -c "import json; data=[]; [data.extend(json.load(open(f'%OUTPUT_DIR%/{f}'))) for f in ['questions_2hop.json','questions_3hop.json','questions_4hop.json']]; json.dump(data, open('%OUTPUT_DIR%/complete_dataset.json','w'), indent=2); print(f'Total: {len(data)} questions')"
if %errorlevel% neq 0 goto error

echo.
echo ============================================================
echo Success! Generated question dataset
echo ============================================================
echo.
echo Location: %OUTPUT_DIR%\complete_dataset.json
echo Total questions: 4000
echo.
echo Breakdown:
echo   2-hop: 2000 questions
echo   3-hop: 1500 questions
echo   4-hop: 500 questions
echo.
pause
goto :eof

:error
echo.
echo ERROR: Dataset generation failed!
pause
exit /b 1
