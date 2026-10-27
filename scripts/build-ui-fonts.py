"""Generate an ignored stylesheet from the user's own original FNT glyphs."""
import argparse,base64,io,struct,urllib.request
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
parser=argparse.ArgumentParser()
parser.add_argument('--server',default='http://127.0.0.1:8783')
parser.add_argument('--encoding',default='cp1251',help='Encoding of the installed game (e.g. cp1251 or cp1252)')
args=parser.parse_args()
OUT=Path(__file__).resolve().parents[1]/'web/site/fonts.css'
styles=[]
for source,family in [('medfont.fnt','Heroes UI'),('bigfont.fnt','Heroes Title')]:
 data=urllib.request.urlopen(args.server.rstrip('/')+'/api/asset?name='+source).read()
 h=data[5];scale=64;em=1024 if h<=16 else 2048
 order=['.notdef'];glyphs={};metrics={};cmap={}
 pen=TTGlyphPen(None);glyphs['.notdef']=pen.glyph();metrics['.notdef']=(6*scale,0)
 for c in range(32,256):
  try:char=bytes([c]).decode(args.encoding)
  except UnicodeDecodeError:continue
  name='uni%04X'%ord(char);a,w,z=struct.unpack_from('<iIi',data,32+c*12)
  off=struct.unpack_from('<I',data,3104+c*4)[0]+4128
  pixels=data[off:off+w*h];pen=TTGlyphPen(None)
  for y in range(h):
   x=0
   while x<w:
    if pixels[y*w+x]!=255:x+=1;continue
    end=x+1
    while end<w and pixels[y*w+end]==255:end+=1
    x0=(a+x)*scale;x1=(a+end)*scale;y0=(h-y-1)*scale;y1=(h-y)*scale
    pen.moveTo((x0,y0));pen.lineTo((x0,y1));pen.lineTo((x1,y1));pen.lineTo((x1,y0));pen.closePath();x=end
  glyphs[name]=pen.glyph();metrics[name]=(max(1,a+w+z)*scale,a*scale);order.append(name);cmap[ord(char)]=name
 fb=FontBuilder(em,isTTF=True);fb.setupGlyphOrder(order);fb.setupCharacterMap(cmap);fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics)
 fb.setupHorizontalHeader(ascent=h*scale,descent=0,lineGap=0)
 fb.setupNameTable({'familyName':family,'styleName':'Regular','uniqueFontIdentifier':family+' local conversion','fullName':family,'psName':family.replace(' ','')})
 fb.setupOS2(sTypoAscender=h*scale,sTypoDescender=0,sTypoLineGap=0,usWinAscent=h*scale,usWinDescent=0)
 fb.setupPost();fb.setupMaxp();fb.font.flavor='woff2';buffer=io.BytesIO();fb.save(buffer)
 encoded=base64.b64encode(buffer.getvalue()).decode()
 styles.append('@font-face{font-family:'+family.replace(' ','')+';src:url(data:font/woff2;base64,'+encoded+') format("woff2");font-display:swap}')
OUT.write_text('\n'.join(styles)+'\n')
print('Generated optional local UI fonts; do not commit '+str(OUT))
