#!/usr/bin/make -f
# Decorator for Linux (also builds on macOS/Windows-MinGW): VST3, LV2 and CLAP with host-drawn controls.
# usage: make -C source/dpf            output: source/dpf/bin/
NAME = Decorator

NAM  = ../NeuralAmpModelerCore/NAM
ADT  = ../AudioDSPTools/dsp
FILES_DSP = \
	DecoratorDPF.cpp \
	$(NAM)/activations.cpp $(NAM)/container.cpp $(NAM)/conv1d.cpp $(NAM)/convnet.cpp $(NAM)/dsp.cpp \
	$(NAM)/get_dsp.cpp $(NAM)/lstm.cpp $(NAM)/ring_buffer.cpp $(NAM)/util.cpp \
	$(NAM)/wavenet/model.cpp $(NAM)/wavenet/a2_fast.cpp $(NAM)/wavenet/slimmable.cpp \
	$(ADT)/dsp.cpp

include ../DPF/Makefile.plugins.mk

BUILD_CXX_FLAGS += -std=gnu++20 -I../eigen -I../NeuralAmpModelerCore -I../NeuralAmpModelerCore/Dependencies/nlohmann -DDECORATOR_NO_IPLUG -DNAM_ENABLE_A2_FAST -DNDEBUG -O3 -Wno-unused-parameter

# GCC rejects a member alias in AudioDSPTools' ResamplingContainer.h that clang accepts
ifneq ($(MACOS),true)
BUILD_CXX_FLAGS += -fpermissive
endif

TARGETS += vst3 lv2_dsp clap
all: $(TARGETS)
