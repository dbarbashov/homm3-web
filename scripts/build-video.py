"""Build the minimal LGPL FFmpeg codecs for original Bink/Smacker resources."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tarfile, urllib.request
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--target',choices=['native','web'],default='native');args=p.parse_args()
VERSION='8.0.3';SHA256='6136812ea6d4e68bdba27e33c2a94382711cdf4f8602ffef056ff792bd6f9818'
archive=ROOT/'.local'/f'ffmpeg-{VERSION}.tar.xz';source=ROOT/'.local'/f'ffmpeg-{VERSION}'
prefix=ROOT/'build'/f'ffmpeg-{args.target}'/'install';build=prefix.parent
stamp=prefix/'version.txt'
if (prefix/'lib/libavformat.a').exists() and stamp.exists() and stamp.read_text()==VERSION:print(prefix);raise SystemExit(0)
archive.parent.mkdir(exist_ok=True);build.mkdir(parents=True,exist_ok=True)
if not archive.exists():urllib.request.urlretrieve(f'https://ffmpeg.org/releases/ffmpeg-{VERSION}.tar.xz',archive)
if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise SystemExit('FFmpeg archive checksum mismatch')
if not source.exists():
 with tarfile.open(archive) as tar:tar.extractall(archive.parent,filter='data')
configure=[str(source/'configure'),f'--prefix={prefix}','--disable-autodetect','--disable-everything','--disable-programs','--disable-doc','--disable-network','--disable-avdevice','--disable-avfilter','--disable-asm','--disable-shared','--enable-static','--enable-small','--enable-avcodec','--enable-avformat','--enable-avutil','--enable-swscale','--enable-swresample','--enable-decoder=bink,smacker,binkaudio_dct,binkaudio_rdft,smackaud,pcm_s16le,pcm_u8','--enable-demuxer=bink,smacker','--enable-protocol=file','--disable-pthreads','--disable-w32threads','--disable-os2threads']
env=os.environ.copy()
if args.target=='web':
 sdk=ROOT/'.local/emsdk/upstream/emscripten';llvm=ROOT/'.local/emsdk/upstream/bin'
 env['PATH']=str(sdk)+os.pathsep+str(llvm)+os.pathsep+env['PATH']
 configure+=['--target-os=none','--arch=wasm32','--enable-cross-compile','--cc=emcc','--cxx=em++','--ar=emar','--ranlib=emranlib','--nm=llvm-nm','--extra-cflags=-O2','--disable-runtime-cpudetect','--disable-inline-asm']
else:configure+=['--cc=clang','--cxx=clang++']
(build/'configure-command.json').write_text(json.dumps(configure,indent=2)+'\n')
subprocess.run(configure,cwd=build,env=env,check=True)
subprocess.run(['make','-j6'],cwd=build,env=env,check=True)
subprocess.run(['make','install'],cwd=build,env=env,check=True)
stamp.write_text(VERSION)
print(prefix)
