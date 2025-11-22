// overlay.cpp - FourYourLanguage Direct2D overlay implementation
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_    // winsock.h'nin eklenmesini engeller
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define NOMINMAX

#include "overlay.h"
#include <winsock2.h>
#include <algorithm>
using namespace std;
#include <ws2tcpip.h>
#include <windows.h>
#include <d2d1.h>
#include <dwrite.h>
#include <thread>
#include <iostream>
#include <sstream>
#include <vector>
#include <string>
#include <codecvt>
#include <chrono>
#include <mutex>

#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "dwrite.lib")
#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "gdi32.lib")

// UTF-8 -> wstring helper
static std::wstring utf8_to_wstring(const std::string& utf8) {
    if (utf8.empty()) return std::wstring();
    int wlen = MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, NULL, 0);
    std::wstring wstr;
    if (wlen > 0) {
        wstr.resize(wlen - 1);
        MultiByteToWideChar(CP_UTF8, 0, utf8.c_str(), -1, &wstr[0], wlen);
    }
    return wstr;
}

// JSON parsing helpers
static bool extract_string_field(const std::string& s, const std::string& key, size_t startPos, std::string& out, size_t& foundPos) {
    foundPos = s.find("\"" + key + "\"", startPos);
    if (foundPos == std::string::npos) return false;
    size_t colon = s.find(':', foundPos);
    if (colon == std::string::npos) return false;
    size_t first_quote = s.find('"', colon + 1);
    size_t second_quote = s.find('"', first_quote + 1);
    if (first_quote == std::string::npos || second_quote == std::string::npos) return false;
    out = s.substr(first_quote + 1, second_quote - first_quote - 1);
    return true;
}

static bool extract_number_field(const std::string& s, const std::string& key, size_t startPos, double& out, size_t& foundPos) {
    foundPos = s.find("\"" + key + "\"", startPos);
    if (foundPos == std::string::npos) return false;
    size_t colon = s.find(':', foundPos);
    if (colon == std::string::npos) return false;
    size_t p = colon + 1;
    while (p < s.size() && (s[p] == ' ' || s[p] == '\t')) ++p;
    size_t end = p;
    while (end < s.size() && (isdigit((unsigned char)s[end]) || s[end] == '.' || s[end] == '-')) ++end;
    if (end == p) return false;
    try { out = std::stod(s.substr(p, end - p)); } catch (...) { return false; }
    return true;
}

static std::vector<TranslationText> parse_translations(const std::string& json) {
    std::vector<TranslationText> out;
    size_t pos = json.find("\"translations\"");
    if (pos == std::string::npos) return out;
    size_t arrStart = json.find('[', pos);
    if (arrStart == std::string::npos) return out;
    size_t i = arrStart + 1;
    while (i < json.size()) {
        size_t objStart = json.find('{', i);
        if (objStart == std::string::npos) break;
        size_t objEnd = json.find('}', objStart);
        if (objEnd == std::string::npos) break;
        std::string obj = json.substr(objStart, objEnd - objStart + 1);
        TranslationText tt;
        tt.text = L"";
        tt.x = tt.y = tt.width = tt.height = 0;
        tt.confidence = 0;
        std::string textUtf8;
        size_t fpos;
        if (extract_string_field(obj, "text", 0, textUtf8, fpos)) tt.text = utf8_to_wstring(textUtf8);
        double tmp;
        if (extract_number_field(obj, "x", 0, tmp, fpos)) tt.x = (float)tmp;
        if (extract_number_field(obj, "y", 0, tmp, fpos)) tt.y = (float)tmp;
        if (extract_number_field(obj, "width", 0, tmp, fpos)) tt.width = (float)tmp;
        if (extract_number_field(obj, "height", 0, tmp, fpos)) tt.height = (float)tmp;
        if (extract_number_field(obj, "confidence", 0, tmp, fpos)) tt.confidence = (int)tmp;
        out.push_back(tt);
        i = objEnd + 1;
    }
    return out;
}

//Direct2DOverlay uygulaması
static Direct2DOverlay* g_instance = nullptr;

Direct2DOverlay::Direct2DOverlay()
    : hwnd_(nullptr), pFactory_(nullptr), pRenderTarget_(nullptr), pBrush_(nullptr),
      pDWriteFactory_(nullptr), pTextFormat_(nullptr) {}

Direct2DOverlay::~Direct2DOverlay() { Shutdown(); }

bool Direct2DOverlay::Initialize(HINSTANCE hInstance, int width, int height) {
    HRESULT hr = D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &pFactory_);
    if (FAILED(hr) || !pFactory_) { MessageBox(NULL, L"D2D1CreateFactory failed", L"Error", MB_OK); return false; }
    hr = DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED, __uuidof(IDWriteFactory), reinterpret_cast<IUnknown**>(&pDWriteFactory_));
    if (FAILED(hr) || !pDWriteFactory_) { MessageBox(NULL, L"DWriteCreateFactory failed", L"Error", MB_OK); return false; }

    WNDCLASS wc = {};
    wc.lpfnWndProc = Direct2DOverlay::StaticWndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = L"FourYourLanguageOverlayClass";
    RegisterClass(&wc);

    int screenW = GetSystemMetrics(SM_CXSCREEN);
    int screenH = GetSystemMetrics(SM_CYSCREEN);
    if (width == 0) width = screenW;
    if (height == 0) height = screenH;

    hwnd_ = CreateWindowEx(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE,
        wc.lpszClassName,
        L"FourYourLanguage Overlay",
        WS_POPUP,
        0, 0, width, height,
        NULL, NULL, hInstance, NULL
    );
    if (!hwnd_) { MessageBox(NULL, L"CreateWindowEx failed", L"Error", MB_OK); return false; }

    SetLayeredWindowAttributes(hwnd_, 0, 200, LWA_ALPHA); // %78 şeffaflık
    SetWindowLong(hwnd_, GWL_EXSTYLE, GetWindowLong(hwnd_, GWL_EXSTYLE) | WS_EX_TRANSPARENT | WS_EX_LAYERED);

    if (!CreateDeviceResources()) { MessageBox(NULL, L"CreateDeviceResources failed", L"Error", MB_OK); return false; }

    hr = pDWriteFactory_->CreateTextFormat(
        L"Segoe UI", NULL, DWRITE_FONT_WEIGHT_BOLD, DWRITE_FONT_STYLE_NORMAL, DWRITE_FONT_STRETCH_NORMAL,
        20.0f, L"en-US", &pTextFormat_);
    if (FAILED(hr)) { MessageBox(NULL, L"CreateTextFormat failed", L"Error", MB_OK); return false; }

    g_instance = this;
    ShowWindow(hwnd_, SW_SHOW);
    UpdateWindow(hwnd_);
    return true;
}

bool Direct2DOverlay::CreateDeviceResources() {
    if (!pFactory_) return false;
    RECT rc; GetClientRect(hwnd_, &rc);
    D2D1_SIZE_U size = D2D1::SizeU(rc.right - rc.left, rc.bottom - rc.top);
    D2D1_HWND_RENDER_TARGET_PROPERTIES props = D2D1::HwndRenderTargetProperties(hwnd_, size);
    HRESULT hr = pFactory_->CreateHwndRenderTarget(D2D1::RenderTargetProperties(), props, &pRenderTarget_);
    if (FAILED(hr) || !pRenderTarget_) return false;
    hr = pRenderTarget_->CreateSolidColorBrush(D2D1::ColorF(D2D1::ColorF::White, 1.0f), &pBrush_);
    if (FAILED(hr) || !pBrush_) return false;
    return true;
}

void Direct2DOverlay::SafeRelease() {
    if (pTextFormat_) { pTextFormat_->Release(); pTextFormat_ = nullptr; }
    if (pBrush_) { pBrush_->Release(); pBrush_ = nullptr; }
    if (pRenderTarget_) { pRenderTarget_->Release(); pRenderTarget_ = nullptr; }
    if (pDWriteFactory_) { pDWriteFactory_->Release(); pDWriteFactory_ = nullptr; }
    if (pFactory_) { pFactory_->Release(); pFactory_ = nullptr; }
}

void Direct2DOverlay::Shutdown() { SafeRelease(); if (hwnd_) { DestroyWindow(hwnd_); hwnd_ = nullptr; } g_instance = nullptr; }

void Direct2DOverlay::UpdateTranslations(const std::vector<TranslationText>& texts) { 
    std::lock_guard<std::mutex> lock(texts_mutex_); 
    current_texts_ = texts; 
    if (hwnd_) InvalidateRect(hwnd_, NULL, TRUE); 
}

void Direct2DOverlay::ClearTranslations() { 
    std::lock_guard<std::mutex> lock(texts_mutex_); 
    current_texts_.clear(); 
    if (hwnd_) InvalidateRect(hwnd_, NULL, TRUE); 
}

void Direct2DOverlay::OnRender() {
    if (!pRenderTarget_) return;
    
    pRenderTarget_->BeginDraw();
    pRenderTarget_->Clear(D2D1::ColorF(0.0f, 0.0f, 0.0f, 0.0f)); // Tam şeffaf arkaplan

    std::lock_guard<std::mutex> lock(texts_mutex_);
    
    for (const auto& t : current_texts_) {
        // Düşük güvenilirlikli metinleri atla
        if (t.confidence < 50) continue;
        
        float fontSize = std::max(14.0f, std::min(24.0f, t.height * 0.9f));
        
        // YAZI TİPİ FORMATI
        IDWriteTextFormat* textFormat = nullptr;
        pDWriteFactory_->CreateTextFormat(
            L"Segoe UI", NULL, 
            DWRITE_FONT_WEIGHT_BOLD, 
            DWRITE_FONT_STYLE_NORMAL, 
            DWRITE_FONT_STRETCH_NORMAL,
            fontSize, L"", &textFormat);
            
        if (textFormat) {
            textFormat->SetTextAlignment(DWRITE_TEXT_ALIGNMENT_CENTER);
            textFormat->SetParagraphAlignment(DWRITE_PARAGRAPH_ALIGNMENT_CENTER);
            
            // ARKA PLAN (Koyu yarı şeffaf - orijinal yazıyı bulanıklaştır)
            ID2D1SolidColorBrush* bgBrush = nullptr;
            pRenderTarget_->CreateSolidColorBrush(
                D2D1::ColorF(0.1f, 0.1f, 0.1f, 0.7f), &bgBrush);
                
            // METİN RENGİ (Beyaz)
            ID2D1SolidColorBrush* textBrush = nullptr;
            pRenderTarget_->CreateSolidColorBrush(
                D2D1::ColorF(1.0f, 1.0f, 1.0f, 1.0f), &textBrush);
            
            if (bgBrush && textBrush) {
                // Orijinal metin kutusunu BULANIKLAŞTIR
                D2D1_RECT_F backgroundRect = D2D1::RectF(
                    t.x - 2, t.y - 1, 
                    t.x + t.width + 2, t.y + t.height + 1
                );
                
                // Arkaplanı çiz (orijinal yazıyı kapatır)
                pRenderTarget_->FillRectangle(backgroundRect, bgBrush);
                
                // Çeviri metnini ORJİNAL YAZININ ÜZERİNE yazar
                D2D1_RECT_F textRect = D2D1::RectF(t.x, t.y, t.x + t.width, t.y + t.height);
                pRenderTarget_->DrawText(
                    t.text.c_str(), 
                    (UINT32)t.text.size(), 
                    textFormat, 
                    textRect, 
                    textBrush
                );
            }
            
            if (bgBrush) bgBrush->Release();
            if (textBrush) textBrush->Release();
            textFormat->Release();
        }
    }
    
    pRenderTarget_->EndDraw();
}

LRESULT CALLBACK Direct2DOverlay::StaticWndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) { 
    if (g_instance) return g_instance->WndProc(hwnd, uMsg, wParam, lParam); 
    return DefWindowProc(hwnd, uMsg, wParam, lParam); 
}

LRESULT CALLBACK Direct2DOverlay::WndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_PAINT:
    case WM_DISPLAYCHANGE: { 
        PAINTSTRUCT ps; 
        BeginPaint(hwnd, &ps); 
        OnRender(); 
        EndPaint(hwnd, &ps); 
    } return 0;
    
    // Tıklama mesajlarını ignore et 
    case WM_LBUTTONDOWN:
    case WM_LBUTTONUP:
    case WM_RBUTTONDOWN:
    case WM_RBUTTONUP:
    case WM_MOUSEMOVE:
    case WM_MOUSEACTIVATE:
        return HTTRANSPARENT; // Tıklamaları altındaki pencereye geçir
    
    case WM_DESTROY: 
        PostQuitMessage(0); 
        return 0;
        
    default: 
        return DefWindowProc(hwnd, uMsg, wParam, lParam);
    }
}

class NetworkClient {
public:
    NetworkClient(Direct2DOverlay* overlay) : overlay_(overlay), sock_(INVALID_SOCKET), running_(false) {}
    ~NetworkClient() { Disconnect(); }

    bool Connect(const char* host, int port) {
        WSADATA wsa;
        if (WSAStartup(MAKEWORD(2,2), &wsa) != 0) return false;
        sock_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_ == INVALID_SOCKET) { WSACleanup(); return false; }
        sockaddr_in srv; srv.sin_family = AF_INET; srv.sin_port = htons(port); inet_pton(AF_INET, host, &srv.sin_addr);
        for (int i=0;i<10;i++) {
            if (connect(sock_, (sockaddr*)&srv, sizeof(srv)) == 0) { running_ = true; recv_thread_ = std::thread(&NetworkClient::ReceiveLoop, this); return true; }
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
        closesocket(sock_); sock_ = INVALID_SOCKET; WSACleanup();
        return false;
    }

    void Disconnect() {
        running_ = false;
        if (recv_thread_.joinable()) recv_thread_.join();
        if (sock_ != INVALID_SOCKET) { closesocket(sock_); sock_ = INVALID_SOCKET; }
        WSACleanup();
    }

private:
    SOCKET sock_;
    Direct2DOverlay* overlay_;
    std::thread recv_thread_;
    bool running_;

    void ReceiveLoop() {
        std::string buffer;
        char tmp[4096];
        while (running_) {
            int r = recv(sock_, tmp, (int)sizeof(tmp)-1, 0);
            if (r <= 0) { running_ = false; break; }
            tmp[r] = '\0';
            buffer.append(tmp, r);
            size_t pos;
            while ((pos = buffer.find('\n')) != std::string::npos) {
                std::string line = buffer.substr(0, pos);
                buffer.erase(0, pos + 1);
                if (line.find("\"type\"") != std::string::npos && line.find("\"update\"") != std::string::npos)
                    overlay_->UpdateTranslations(parse_translations(line));
                else if (line.find("\"type\"") != std::string::npos && line.find("\"clear\"") != std::string::npos)
                    overlay_->ClearTranslations();
            }
        }
    }
};

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int) {
    Direct2DOverlay overlay;
    if (!overlay.Initialize(hInstance, 0, 0)) { MessageBox(NULL, L"Overlay initialization failed", L"Error", MB_OK); return -1; }
    NetworkClient client(&overlay);
    client.Connect("127.0.0.1", 8888);

    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0)) { TranslateMessage(&msg); DispatchMessage(&msg); }

    client.Disconnect();
    overlay.Shutdown();
    return 0;
}