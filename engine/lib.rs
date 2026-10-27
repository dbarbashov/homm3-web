//! Browser ABI around the unmodified CC0 homm3-decomp resource readers.
//! This is a map/graphics foundation, not the reconstructed game runtime.
use std::{fmt::Write, sync::Mutex};
use homm3_map::{MapHeader, WorldPrefix, Terrain, ObjectTable, MapBody};
use homm3_def::Sprite;

static INPUT: Mutex<Vec<u8>> = Mutex::new(Vec::new());
static OUTPUT: Mutex<Vec<u8>> = Mutex::new(Vec::new());

// JS writes the buffer only between calls. No Rust reference remains borrowed.
#[no_mangle]
pub extern "C" fn input_buffer(length: usize) -> *mut u8 {
    if length > 128 * 1024 * 1024 { return std::ptr::null_mut(); }
    let mut input = INPUT.lock().unwrap();
    input.resize(length, 0);
    input.as_mut_ptr()
}
#[no_mangle]
pub extern "C" fn output_ptr() -> *const u8 { OUTPUT.lock().unwrap().as_ptr() }
#[no_mangle]
pub extern "C" fn output_len() -> usize { OUTPUT.lock().unwrap().len() }

fn finish(result: Result<Vec<u8>, String>) -> i32 {
    let (status, data) = match result {
        Ok(data) => (1, data), Err(error) => (0, error.into_bytes()),
    };
    *OUTPUT.lock().unwrap() = data;
    status
}
fn err(e: impl std::fmt::Debug) -> String { format!("{e:?}") }
// JSON uses byte arrays for game strings so the browser can select a legacy encoding.
fn bytes(out: &mut String, value: &[u8]) {
    out.push('[');
    for (i, b) in value.iter().enumerate() {
        if i > 0 { out.push(','); }
        write!(out, "{b}").unwrap();
    }
    out.push(']');
}

#[no_mangle]
pub extern "C" fn parse_map() -> i32 {
    finish((|| {
        let input = INPUT.lock().unwrap();
        let header = MapHeader::parse(&input).map_err(err)?;
        if !(1..=252).contains(&header.size) { return Err("Unsupported map dimensions".into()); }
        let prefix = WorldPrefix::parse(header.world(), header.version).map_err(err)?;
        let terrain = Terrain::parse(prefix.map(), header.size, header.two_layers).map_err(err)?;
        let table = ObjectTable::parse(terrain.objects()).map_err(err)?;
        let body = MapBody::parse(table, header.version).map_err(err)?;
        let mut out = format!("{{\"size\":{},\"layers\":{},\"version\":{},\"name\":",header.size,terrain.layers(),header.version as i32);
        bytes(&mut out, header.name.bytes());
        out.push_str(",\"description\":"); bytes(&mut out, header.description.bytes());
        out.push_str(",\"players\":[");
        for (i,p) in header.players.iter().enumerate() {
            if i>0 {out.push(',');}
            write!(out,"{{\"human\":{},\"computer\":{},\"town\":{},\"position\":{:?}}}",p.can_be_human,p.can_be_computer,p.has_main_town,p.main_town).unwrap();
        }
        out.push_str("],\"terrain\":[");
        for i in 0..terrain.len() {
            if i>0 {out.push(',');}
            let t=terrain.cell(i).unwrap();
            write!(out,"[{},{},{},{},{},{},{}]",t.ground_set as u8,t.ground_index as u8,t.river_set as u8,t.river_index as u8,t.road_set as u8,t.road_index as u8,t.flags).unwrap();
        }
        out.push_str("],\"types\":[");
        for (i,t) in table.types().enumerate() {
            if i>0 {out.push(',');}
            out.push_str("{\"name\":"); bytes(&mut out,t.image_name.bytes());
            write!(out,",\"class\":{},\"extra\":{},\"group\":{},\"hidden\":{},\"passable\":",t.object_class,t.extra,t.group,t.suppress_draw).unwrap();
            bytes(&mut out,t.passable);out.push_str(",\"trigger\":"); bytes(&mut out,t.trigger);out.push('}');
        }
        out.push_str("],\"objects\":[");
        for (i,o) in body.objects().enumerate() {
            if i>0 {out.push(',');}
            write!(out,"{{\"position\":{:?},\"type\":{},\"class\":{},\"extra\":{}}}",o.coordinates,o.type_index,o.object_class,o.extra).unwrap();
        }
        write!(out,"],\"events\":{},\"trailing\":{}}}",body.timed_events().len(),body.trailing().len()).unwrap();
        Ok(out.into_bytes())
    })())
}

#[no_mangle]
pub extern "C" fn sprite_info() -> i32 {
    finish((|| {
        let input=INPUT.lock().unwrap();
        let sprite=Sprite::parse(&input).map_err(err)?;
        let h=sprite.header();
        let mut out=format!("{{\"width\":{},\"height\":{},\"kind\":{},\"groups\":[",h.width,h.height,h.kind.0);
        for i in 0..sprite.group_count() {
            if i>0 {out.push(',');}
            let g=sprite.group(i).map_err(err)?;
            write!(out,"{{\"id\":{},\"count\":{}}}",g.id(),g.len()).unwrap();
        }
        out.push_str("]}");Ok(out.into_bytes())
    })())
}

// Binary output: six i32 (full w/h, crop w/h, crop x/y), then RGBA pixels.
#[no_mangle]
pub extern "C" fn sprite_frame(group: usize, index: usize, opaque: u32) -> i32 {
    finish((|| {
        let input=INPUT.lock().unwrap();
        let sprite=Sprite::parse(&input).map_err(err)?;
        let frame=sprite.group(group).map_err(err)?.frame(index).map_err(err)?;
        let count=frame.pixel_len().map_err(err)?;
        if count>16*1024*1024 {return Err("Frame too large".into());}
        let mut indexed=vec![0;count];frame.decode_into(&mut indexed).map_err(err)?;
        let mut out=Vec::with_capacity(24+count*4);
        for n in [frame.width() as i32,frame.height() as i32,frame.cropped_width() as i32,frame.cropped_height() as i32,frame.cropped_x(),frame.cropped_y()] {
            out.extend_from_slice(&n.to_le_bytes());
        }
        for index in indexed {
            let rgb=sprite.palette().rgb(index);
            // Browser compositing approximation of the original 16-bit shadows.
            let pixel=if opaque != 0 { [rgb[0],rgb[1],rgb[2],255] }
                else {match index {
                    0 => [0,0,0,0],
                    1 => [0,0,0,64],
                    2 => [0,0,0,128],
                    3 => [0,0,0,192],
                    4 => [0,0,0,128],
                    _ => [rgb[0],rgb[1],rgb[2],255],
                }};
            out.extend_from_slice(&pixel);
        }
        Ok(out)
    })())
}
