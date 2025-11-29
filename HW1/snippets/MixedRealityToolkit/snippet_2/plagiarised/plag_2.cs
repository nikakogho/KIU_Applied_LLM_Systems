/// <summary>
/// Slider callback: spins and scales the object around its initial state.
/// </summary>
public void SpinObjectWithSlider(SliderEventData args)
{
    if (initialSliderValue < 0f)
    {
        initialRotation = transform.localRotation;
        initialScale = transform.localScale;
        initialSliderValue = args.NewValue; // cache first value
    }

    // Compute offset from original slider position.
    var sliderOffset = args.NewValue - initialSliderValue;

    var rotation = Quaternion.AngleAxis(-90f * sliderOffset, Vector3.up);
    transform.localRotation = initialRotation * rotation;

    var scaleFactor = 1f + 0.2f * sliderOffset;
    transform.localScale = initialScale * scaleFactor;
}
