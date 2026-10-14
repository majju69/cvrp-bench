CXX = clang++
CXXFLAGS = -O2 -std=c++20 -Wall -Wextra

build/cvrp_solve: cpp/cvrp_solve.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) $< -o $@

test: build/cvrp_solve
	uv run pytest -q

clean:
	rm -rf build

.PHONY: test clean