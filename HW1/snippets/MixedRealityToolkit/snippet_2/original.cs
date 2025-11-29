/// <summary>
/// Hook up to a slider's OnValueChanged event.
/// </summary>
public void SpinObjectWithSlider(SliderEventData args)
{
    // If this is our first slider event, let's record the initial values.
    if (initialSliderValue < 0)
    {
        initialRotation = transform.localRotation;
        initialScale = transform.localScale;
        initialSliderValue = args.NewValue;
    }

    // Adjust the gem based on the difference between the current slider's value and where it started.
    float sliderDelta = args.NewValue - initialSliderValue;
    transform.localRotation = initialRotation * Quaternion.AngleAxis(sliderDelta * -90, Vector3.up);
    transform.localScale = initialScale * (1 + sliderDelta * 0.2f);
}