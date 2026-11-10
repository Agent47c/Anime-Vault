"""Lossless handling of JPEG ICC metadata that Qt cannot use."""
from pathlib import Path
import os
import tempfile


def repair_jpeg_profile(data):
    """Repair short text tags; drop printer profiles Qt already ignores.

    JPEG scan data and supported profiles stay byte-identical.
    Unrecognised/malformed structures are left alone rather than guessed at.
    """
    if not data.startswith(b'\xff\xd8'):return data
    parts={};segments=[];count=None;position=2
    while position+4<=len(data):
        if data[position]!=255:return data
        marker_start=position
        while position<len(data) and data[position]==255:position+=1
        if position>=len(data):return data
        marker=data[position];position+=1
        if marker in (0xda,0xd9):break
        if marker in (0x01,*range(0xd0,0xd8)):continue
        size=int.from_bytes(data[position:position+2],'big');start=position+2;end=position+size
        if size<2 or end>len(data):return data
        if marker==0xe2 and data[start:start+12]==b'ICC_PROFILE\0':
            if start+14>end:return data
            sequence,total=data[start+12:start+14]
            if not sequence or sequence>total or sequence in parts or (count is not None and count!=total):return data
            count=total;parts[sequence]=(start+14,end)
            segments.append((marker_start,end))
        position=end
    if not count or len(parts)!=count:return data
    profile=b''.join(data[s:e] for s,e in (parts[n] for n in range(1,count+1)))
    if len(profile)<132 or profile[36:40]!=b'acsp' or int.from_bytes(profile[:4],'big')!=len(profile):return data
    if profile[12:16]==b'prtr':
        # Output/printer profiles aren't supported by Qt's image colour space.
        # Do not mislabel one as a monitor profile or recompress the image.
        chunks=[];offset=0
        for start,end in segments:
            chunks.append(data[offset:start]);offset=end
        chunks.append(data[offset:])
        return b''.join(chunks)
    number=int.from_bytes(profile[128:132],'big');table_end=132+12*number
    if table_end>len(profile):return data
    tags=[]
    for n in range(number):
        entry=132+n*12;offset=int.from_bytes(profile[entry+4:entry+8],'big');size=int.from_bytes(profile[entry+8:entry+12],'big')
        if offset<table_end or offset+size>len(profile):return data
        tags.append((entry,offset,size))
    result=bytearray(profile);changed=False
    for entry,offset,size in tags:
        if profile[entry:entry+4]!=b'cprt' or not 8<=size<12 or profile[offset:offset+4]!=b'text':continue
        if offset+12>len(profile) or any(profile[offset+size:offset+12]):continue
        if any(other!=entry and at<offset+12 and at+length>offset+size for other,at,length in tags):continue
        result[entry+8:entry+12]=(12).to_bytes(4,'big');changed=True
    if not changed:return data
    # A zero ID explicitly means no profile checksum is supplied.
    result[84:100]=bytes(16)
    output=bytearray(data);offset=0
    for n in range(1,count+1):
        start,end=parts[n];output[start:end]=result[offset:offset+end-start];offset+=end-start
    return bytes(output)


def load_cached_image(path):
    """Decode and opportunistically repair an artwork cache in its worker."""
    from PyQt5.QtGui import QImage
    path=Path(path)
    try:original=path.read_bytes()
    except OSError:return QImage()
    cleaned=repair_jpeg_profile(original)
    image=QImage.fromData(cleaned)
    if cleaned!=original and not image.isNull():
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent,prefix=path.name+'.',suffix='.profile',delete=False) as stream:
                temporary=Path(stream.name);stream.write(cleaned)
            # Don't replace artwork changed concurrently by another writer.
            if path.read_bytes()==original:os.replace(temporary,path)
        except OSError:pass  # An unwritable cache still decodes the repaired bytes.
        finally:
            if temporary is not None:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass
    return image
