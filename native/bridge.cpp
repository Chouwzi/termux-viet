// SPDX-License-Identifier: GPL-2.0-or-later
#include "ukengine.h"
#include <mutex>
#include <new>

#define TV_API extern "C" __attribute__((visibility("default")))

namespace {
struct Context {
    UkSharedMem shared{};
    UkEngine engine;
    bool shift = false;

    explicit Context(bool modern) {
        static std::once_flag initialized;
        std::call_once(initialized, SetupUnikeyEngine);
        shared.input.init();
        shared.macStore.init();
        shared.vietKey = true;
        shared.input.setIM(UkTelex);
        shared.charsetId = CONV_CHARSET_XUTF8;
        shared.options.freeMarking = 1;
        shared.options.modernStyle = modern;
        shared.options.spellCheckEnabled = 1;
        engine.setCtrlInfo(&shared);
        engine.setCheckKbCaseFunc([this](int *pressed, int *caps) {
            *pressed = shift;
            *caps = 0;
        });
    }
};
}

TV_API void *tv_create(int modern) noexcept {
    try { return new Context(modern != 0); }
    catch (...) { return nullptr; }
}

TV_API void tv_destroy(void *handle) noexcept {
    delete static_cast<Context *>(handle);
}

TV_API void tv_reset(void *handle) noexcept {
    if (handle) static_cast<Context *>(handle)->engine.reset();
}

TV_API int tv_edit(void *handle, int key, int *backs,
                   unsigned char *output, int capacity) noexcept {
    if (!handle || !backs || !output || capacity < 1024 || key < -1 || key > 127)
        return -1;
    try {
        auto &context = *static_cast<Context *>(handle);
        UkOutputType type;
        int size = capacity;
        *backs = 0;
        if (key == -1) {
            context.engine.processBackspace(*backs, output, size, type);
            if (*backs == 0) *backs = 1;
        } else {
            context.shift = key >= 'A' && key <= 'Z';
            const int handled = context.engine.process(key, *backs, output, size, type);
            if (!handled) {
                output[0] = static_cast<unsigned char>(key);
                size = 1;
            }
        }
        return size;
    } catch (...) {
        static_cast<Context *>(handle)->engine.reset();
        return -1;
    }
}
