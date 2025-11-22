#pragma once
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_
#include <winsock2.h>
#include <windows.h>
#include <d2d1.h>
#include <dwrite.h>
#include <string>
#include <vector>
#include <mutex>

// Tek bir çeviri öğesini tutan yapı
struct TranslationText {
    std::wstring text;
    float x;
    float y;
    float width;
    float height;
    int confidence;
};

class Direct2DOverlay {
public:
    Direct2DOverlay();
    ~Direct2DOverlay();

    //overlay penceresini ve Direct2D kaynaklarını başlat
    bool Initialize(HINSTANCE hInstance, int width = 0, int height = 0);

    // mesaj döngüsünü çalıştır
    void RunMessageLoop();

    // kapatma ve temizleme
    void Shutdown();

    // iş parçacığı tarafından güncellenen çeviri metinlerini ayarla
    void UpdateTranslations(const std::vector<TranslationText>& texts);
    void ClearTranslations();

private:
    HWND hwnd_;
    ID2D1Factory* pFactory_;
    ID2D1HwndRenderTarget* pRenderTarget_;
    ID2D1SolidColorBrush* pBrush_;
    IDWriteFactory* pDWriteFactory_;
    IDWriteTextFormat* pTextFormat_;

    std::vector<TranslationText> current_texts_;
    std::mutex texts_mutex_;

    bool CreateDeviceResources();
    void SafeRelease();
    void OnRender();

    static LRESULT CALLBACK StaticWndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
    LRESULT CALLBACK WndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam);
};

