from PIL import Image
S=2339/1170
C={
 'sky':(2,(0,0,1170,157)),
 'step1':(2,(403,349,564,491)),'step2':(2,(929,349,1090,491)),'step3':(2,(403,567,564,709)),'step4':(2,(929,567,1090,709)),
 'kyujin':(4,(119,320,281,542)),'workin':(4,(626,331,798,542)),
 'sakai':(5,(122,321,268,538)),'yane':(5,(630,346,788,452)),
 'web_visual':(6,(88,325,298,536)),'web_phones':(6,(320,330,535,535)),'web_site':(6,(626,325,903,468)),
 'mv_thumb':(7,(79,365,299,494)),'mv_scene':(7,(308,365,516,494)),'gan_thumb':(7,(627,365,856,494)),
 'trick':(8,(86,326,295,535)),'poster':(8,(642,325,795,540)),'novelty':(8,(833,326,1090,535)),
 'booth':(9,(79,338,304,507)),'pv':(9,(626,325,851,536)),'pv_poster':(9,(902,321,1056,540)),
 'fm':(10,(79,345,240,505)),'record':(10,(636,330,838,535)),
 'signage':(11,(120,325,270,536)),'umeda':(11,(318,325,543,536)),'station':(11,(626,325,851,536)),
 'building':(12,(779,120,1170,827)),
}
for k,(p,b) in C.items():
    im=Image.open(f'pages/p-{p:02d}.png').convert('RGB')
    im.crop(tuple(int(v*S) for v in b)).save(f'img/{k}.jpg',quality=92)
# contact sheet
import glob,os
fs=sorted(glob.glob('img/*.jpg')); W=6; th=220
sheet=Image.new('RGB',(W*th,((len(fs)+W-1)//W)*th),'white')
for i,f in enumerate(fs):
    im=Image.open(f); im.thumbnail((th-10,th-10)); sheet.paste(im,((i%W)*th,(i//W)*th))
sheet.save('sheet.jpg')
print(len(fs))
