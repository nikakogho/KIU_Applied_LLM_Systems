/// <summary>
/// Called when the slider value changes to rotate and scale this object.
/// </summary>
public void SpinObjectWithSlider(SliderEventData args)
{
    // Record starting values the first time we see the slider.
    if (initialSliderValue < 0f)
    {
        initialRotation = transform.localRotation;
        initialScale = transform.localScale;
        initialSliderValue = args.NewValue;
    }

    // Difference from the starting slider position.
    float delta = args.NewValue - initialSliderValue;

    transform.localRotation = initialRotation *
                              Quaternion.AngleAxis(delta * -90f, Vector3.up);

    transform.localScale = initialScale * (1f + delta * 0.2f);
}
