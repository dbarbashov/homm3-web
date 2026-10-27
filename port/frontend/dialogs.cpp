// Text-only front-end normalDialog adapter. Layout comes from the original
// calculateNormalDialogSize, chrome from TDialogBox and all controls are upstream.
// Item/army dialogs belong to the full kb.cpp game lifecycle and are rejected here.
#include "frontend_bridge.h"
#include "dialogbox.h"
#include "kb.h"
#include "button.h"
#include "border.h"
#include "textwdgt.h"
#include "textscroller.h"
#include "font.h"
#include "message.h"
#include "winmgr.h"
#include <memory>
#include <stdexcept>
font* g_mediumFont=nullptr;
namespace {
int popupHandler(message& msg){
    if(msg.m_id==MESSAGE_RIGHT_BUTTON_UP || msg.m_id==MESSAGE_KEY_DOWN){
        g_windowManager->m_dialogReturn=DIALOG_RETURN_OK;
        msg.m_id=MESSAGE_WIDGET;msg.m_codeX=widget::WIDGET_END_DIALOG;
        return MESSAGE_DISPATCH_FORWARD;
    }
    return MESSAGE_DISPATCH_CONSUME;
}
int buttonHandler(message& msg){
    if(msg.m_id==MESSAGE_WIDGET && msg.m_codeX==widget::WIDGET_DESELECT){
        g_windowManager->m_dialogReturn=msg.m_codeY;
        msg.m_codeX=widget::WIDGET_END_DIALOG;
        return MESSAGE_DISPATCH_FORWARD;
    }
    return MESSAGE_DISPATCH_CONSUME;
}
}
void normalDialog(const char* text,int mbType,int x,int y,int resType1,int,int resType2,int,int,int timeout,int resType3,int){
    if(resType1!=-1 || resType2!=-1 || resType3!=-1 || timeout>0)
        throw std::runtime_error("Item and timed dialogs need the full kb.cpp lifecycle");
    if(mbType!=NORMAL_DIALOG_DEFAULT && mbType!=NORMAL_DIALOG_YESNO && mbType!=NORMAL_DIALOG_POPUP)
        throw std::runtime_error("Unsupported front-end dialog type");
    TNormalDialogInfo info{};
    info.m_dialogText=text?text:"";info.m_x=x;info.m_y=y;
    info.m_textWidgetX=20;info.m_textWidgetY=30;info.m_mbType=static_cast<EMBType>(mbType);
    for(auto& icon:info.m_icons)icon.m_resource=const_no_resource;
    calculateNormalDialogSize(info);
    TDialogBox dialog(info.m_x,info.m_y,info.m_width,info.m_height,0x12);
    std::vector<std::unique_ptr<widget>> controls;
    auto add=[&](widget* w){controls.emplace_back(w);dialog.addWidget(w,-1);};
    if(info.m_textExpansion)
        add(new type_text_scroller(info.m_dialogText.c_str(),info.m_textWidgetX,info.m_textWidgetY,info.m_textWidgetWidth,info.m_textWidgetHeight,"medfont.fnt",font::PRIMARY,slider::BROWN));
    else
        add(new textWidget(info.m_textWidgetX,info.m_textWidgetY,info.m_textWidgetWidth,info.m_textWidgetHeight,info.m_dialogText.c_str(),"medfont.fnt",font::PRIMARY,1,font::CENTER_JUSTIFIED,0,8));
    auto addButton=[&](int bx,int id,const char* image,int key){
        int by=info.m_height-62;
        add(new bitmapBorder(bx,by,66,32,id+100,"Box64x30.pcx",0x800));
        add(new button(bx+1,by+1,64,30,id,image,0,1,false,key,2));
    };
    if(mbType==NORMAL_DIALOG_YESNO){
        addButton(info.m_width/2-74,DIALOG_RETURN_ACCEPT,"iOkay.def",0x1c);
        addButton(info.m_width/2+8,DIALOG_RETURN_DECLINE,"iCancel.def",1);
    }else if(mbType==NORMAL_DIALOG_DEFAULT)addButton((info.m_width-66)/2,DIALOG_RETURN_OK,"iOkay.def",0x1c);
    Port::runDialog(&dialog,mbType==NORMAL_DIALOG_POPUP?popupHandler:buttonHandler,0,mbType==NORMAL_DIALOG_YESNO?"confirm":"message");
    // The original window manager has detached controls before their owners die.
}
