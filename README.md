# assdumper

TS 内のAプロファイルの字幕を ASS (Advanced SubStation Alpha) に変換するスクリプトです。

## 動作環境

python 3.9 で動作を確認しています。  

## オプション

* -i, --input: 入力 TS ファイルを指定します。省略された場合は標準入力になります。
* -o, --output: 出力先の ASS ファイルを指定します。省略された場合は標準出力になります。
* -s, --SID: 対象の サービスID を指定します。 (必須)
* -a, --accurate: ARIB字幕っぽさを出す工夫を無効化します
