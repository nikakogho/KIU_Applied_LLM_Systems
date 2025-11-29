/// <summary>
/// Use the slider to twist and resize this object.
/// </summary>
public void SpinObjectWithSlider(SliderEventData args)
{
    // Initialize baseline on first use.
    if (initialSliderValue < 0f)
    {
        initialSliderValue = args.NewValue;
        initialRotation = transform.localRotation;
        initialScale = transform.localScale;
    }

    float sliderDelta = args.NewValue - initialSliderValue;

    // Y-rotation based on sliderDelta.
    transform.localRotation = initialRotation *
                              Quaternion.AngleAxis(-90f * sliderDelta, Vector3.up);

    // Uniform scale based on sliderDelta.
    transform.localScale = initialScale * (1f + 0.2f * sliderDelta);
}
