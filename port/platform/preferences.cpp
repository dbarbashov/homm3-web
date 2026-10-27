// Portable backing store for the original ReadPrefs/WritePrefs registry calls.
// Values retain their original names and types; no raw configStruct is saved.
#include "windows.h"
#include <fstream>
#include <sstream>
#include <map>
#include <memory>
#include <vector>
#include <string>
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#endif
namespace {
struct Value {DWORD type;std::vector<BYTE> bytes;};
struct Key {std::string path;};
std::map<std::string,Value> values;
bool loaded=false,dirty=false;
std::string lower(std::string s){for(char& c:s)c=std::tolower(static_cast<unsigned char>(c));return s;}
std::string hex(const BYTE* p,size_t n){const char* digits="0123456789abcdef";std::string s;for(size_t i=0;i<n;++i){s+=digits[p[i]>>4];s+=digits[p[i]&15];}return s;}
std::vector<BYTE> unhex(const std::string& s){
    if(s.size()%2 || s.size()>8192)throw std::runtime_error("invalid preferences value");
    std::vector<BYTE> out;for(size_t i=0;i<s.size();i+=2){
        auto nibble=[](char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;throw std::runtime_error("invalid preferences hex");};
        out.push_back((nibble(s[i])<<4)|nibble(s[i+1]));
    }return out;
}
void load(){
    if(loaded)return;loaded=true;
    std::ifstream in("preferences.dat");std::string header;if(!std::getline(in,header))return;
    if(header!="H3PREF1")return;
    try{
        std::string line;std::map<std::string,Value> parsed;
        while(std::getline(in,line)){
            if(parsed.size()>=1024)throw std::runtime_error("too many preferences");
            std::istringstream row(line);std::string name,data;DWORD type;
            if(!(row>>name>>type>>data) || (type!=REG_DWORD && type!=REG_SZ))throw std::runtime_error("invalid preferences record");
            auto key=unhex(name),bytes=unhex(data);
            if(key.empty() || (type==REG_DWORD && bytes.size()!=4))throw std::runtime_error("invalid preference size");
            parsed.emplace(std::string(key.begin(),key.end()),Value{type,std::move(bytes)});
        }values=std::move(parsed);
    }catch(const std::exception&){values.clear();}
}
LONG save(){
    if(!dirty)return ERROR_SUCCESS;
    std::ostringstream data;data<<"H3PREF1\n";
    for(const auto& entry:values)data<<hex(reinterpret_cast<const BYTE*>(entry.first.data()),entry.first.size())<<' '<<entry.second.type<<' '<<hex(entry.second.bytes.data(),entry.second.bytes.size())<<'\n';
    const auto text=data.str();
    FILE* file=fopen("preferences.dat.tmp","wb");if(!file)return 5;
    bool ok=fwrite(text.data(),1,text.size(),file)==text.size();if(fclose(file))ok=false;
    if(!ok || rename("preferences.dat.tmp","preferences.dat"))return 5;
#ifdef __EMSCRIPTEN__
    const int persisted=EM_ASM_INT({
        try {localStorage.setItem('homm3.preferences.v1',UTF8ToString($0));window.homm3SettingsSaved=true;return 1;}
        catch(error){window.dispatchEvent(new CustomEvent('homm3-storage-error',{detail:String(error)}));return 0;}
    },text.c_str());
    if(!persisted)return 5;
#endif
    dirty=false;return ERROR_SUCCESS;
}
LONG keyFor(HKEY parent,const char* name,HKEY* result){
    if(!name || !result)return 87;load();
    std::string prefix;
    if(parent && parent!=HKEY_LOCAL_MACHINE)prefix=static_cast<Key*>(parent)->path+"\\";
    *result=static_cast<HKEY>(new Key{lower(prefix+name)});return ERROR_SUCCESS;
}
}
extern "C" LONG RegOpenKeyExA(HKEY parent,const char* name,DWORD,DWORD,HKEY* result){return keyFor(parent,name,result);}
extern "C" LONG RegCreateKeyA(HKEY parent,const char* name,HKEY* result){return keyFor(parent,name,result);}
extern "C" LONG RegCloseKey(HKEY key){delete static_cast<Key*>(key);return save();}
extern "C" LONG RegQueryValueExA(HKEY key,const char* name,DWORD*,DWORD* type,BYTE* data,DWORD* size){
    if(!key || !name || !size)return 87;
    auto found=values.find(static_cast<Key*>(key)->path+"/"+lower(name));if(found==values.end())return 2;
    const auto& value=found->second;if(type)*type=value.type;
    DWORD capacity=*size;*size=value.bytes.size();if(!data)return ERROR_SUCCESS;
    if(capacity<value.bytes.size())return 234;
    std::copy(value.bytes.begin(),value.bytes.end(),data);return ERROR_SUCCESS;
}
extern "C" LONG RegSetValueExA(HKEY key,const char* name,DWORD,DWORD type,const BYTE* data,DWORD size){
    if(!key || !name || !data || !size || size>4096 || (type!=REG_DWORD && type!=REG_SZ) || (type==REG_DWORD && size!=4))return 87;
    Value value{type,std::vector<BYTE>(data,data+size)};
    if(type==REG_SZ && value.bytes.back()!=0)value.bytes.push_back(0);
    const auto id=static_cast<Key*>(key)->path+"/"+lower(name);auto found=values.find(id);
    if(found==values.end() || found->second.type!=type || found->second.bytes!=value.bytes){values[id]=std::move(value);dirty=true;}
    return ERROR_SUCCESS;
}
