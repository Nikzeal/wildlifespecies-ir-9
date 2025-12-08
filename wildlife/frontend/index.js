function initDualSlider(wrapper) {
    const minLimit = parseInt(wrapper.dataset.min);
    const maxLimit = parseInt(wrapper.dataset.max);

    const minInput = wrapper.querySelector(".min-input");
    const maxInput = wrapper.querySelector(".max-input");

    const track = wrapper.querySelector(".track");
    const highlight = wrapper.querySelector(".range-highlight");
    const handleMin = wrapper.querySelector(".handle-min");
    const handleMax = wrapper.querySelector(".handle-max");

    let minValue = parseInt(minInput.value);
    let maxValue = parseInt(maxInput.value);

    function updateUI() {
        const trackWidth = track.offsetWidth;

        const leftPos = (minValue - minLimit) / (maxLimit - minLimit) * trackWidth;
        const rightPos = (maxValue - minLimit) / (maxLimit - minLimit) * trackWidth;

        handleMin.style.left = leftPos + "px";
        handleMax.style.left = rightPos + "px";

        highlight.style.left = leftPos + "px";
        highlight.style.width = (rightPos - leftPos) + "px";

        minInput.value = minValue;
        maxInput.value = maxValue;
    }

    function handleDrag(handle, isMin) {
        handle.addEventListener("mousedown", e => {
            function move(ev) {
                const rect = track.getBoundingClientRect();
                let x = ev.clientX - rect.left;

                x = Math.max(0, Math.min(x, rect.width));
                const value = Math.round(x / rect.width * (maxLimit - minLimit) + minLimit);

                if (isMin) {
                    minValue = Math.min(value, maxValue - 1);
                } else {
                    maxValue = Math.max(value, minValue + 1);
                }
                updateUI();
            }

            function stop() {
                document.removeEventListener("mousemove", move);
                document.removeEventListener("mouseup", stop);
            }

            document.addEventListener("mousemove", move);
            document.addEventListener("mouseup", stop);
        });
    }

    minInput.addEventListener("input", () => {
        minValue = Math.max(minLimit, Math.min(parseInt(minInput.value), maxValue - 1));
        updateUI();
    });

    maxInput.addEventListener("input", () => {
        maxValue = Math.min(maxLimit, Math.max(parseInt(maxInput.value), minValue + 1));
        updateUI();
    });

    handleDrag(handleMin, true);
    handleDrag(handleMax, false);

    updateUI();
}

document.querySelectorAll(".range-wrapper").forEach(initDualSlider);