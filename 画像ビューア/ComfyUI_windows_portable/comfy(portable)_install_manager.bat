@echo off
rem ** Save this file in Shift_JIS encoding (Japanese-language version) **
cd /d %~dp0

echo ** このバッチファイルの説明 **
echo ComfyUI Manager をインストールします（Portable版向け）．
echo.
echo ComfyUI のインストールが完了している必要があります．
echo この後、画面の表示が消去されますが正常な動作です．
echo.

if not exist ".\ComfyUI\custom_nodes\" (
  call :ErrorExit ".\ComfyUI\custom_nodes\ のフォルダが存在しないので、バッチファイルの実行を中止します．"
)

if exist ".\ComfyUI\custom_nodes\ComfyUI-Manager\" (
  call :ErrorExit ".\ComfyUI\custom_nodes\ComfyUI-Manager\ のフォルダが存在するので、バッチファイルの実行を中止します．"
)

if not exist ".\python_embeded\python.exe" (
  call :ErrorExit ".\python_embeded\python.exe のファイルが存在しないので、バッチファイルの実行を中止します．"
)

cd .\ComfyUI
pause
echo.

echo ** GitPython のインストール **
@echo on
..\python_embeded\python.exe -s -m pip install gitpython
@echo off
echo.

echo ** message **
echo エラーが出ている場合は内容を確認して、バッチファイルの実行を中止してください．
echo （GitPython がインストール済みの場合は、Requirement already satisfied と表示されますが正常です．）
echo 次に、ComfyUI Manager のダウンロードを行います．
echo.
pause
echo.

echo ** ComfyUI Manager のダウンロード **
echo.
echo ** message **
echo ダウンロードの進捗は表示されないので、そのままお待ちください．
@echo on
..\python_embeded\python.exe -c "import git; git.Repo.clone_from('https://github.com/ltdrdata/ComfyUI-Manager', './custom_nodes/ComfyUI-Manager')"
@echo off
echo.
echo ** message **
echo エラーが出ている場合は内容を確認して、バッチファイルの実行を中止してください．
echo （何も表示されていなければ正常に処理されています．）
echo 次に、必要なパッケージのインストールを行います．
echo.
pause

echo.
echo ** パッケージのインストール **
@echo on
..\python_embeded\python.exe -m pip install -r ./custom_nodes/ComfyUI-Manager/requirements.txt
@echo off
echo.

echo ** message **
echo ComfyUI Manager のインストール処理が終わりました．
echo.
echo バッチファイルの実行を終了します．
echo エラーが出ている場合は内容を確認してください．
echo （黄色い文字の WARNING が表示されていてもは問題ありません.）
echo.
pause

goto :EOF

:ErrorExit
echo ** ERROR **
echo %~1
if not "%~2"=="" echo %~2
echo.
pause

exit
