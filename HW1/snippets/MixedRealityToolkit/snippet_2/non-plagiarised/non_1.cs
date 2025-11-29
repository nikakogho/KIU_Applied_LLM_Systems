private bool _baselineCaptured;

/// <summary>
/// Public handler that can be wired to a slider event to rotate and resize the object.
/// </summary>
public void OnSliderChanged(SliderEventData args)
{
    EnsureBaseline(args.NewValue);

    float offsetFromStart = args.NewValue - initialSliderValue;
    ApplyRotationAndScale(offsetFromStart);
}

private void EnsureBaseline(float currentSliderValue)
{
    if (_baselineCaptured)
    {
        return;
    }

    initialRotation = transform.localRotation;
    initialScale = transform.localScale;
    initialSliderValue = currentSliderValue;

    _baselineCaptured = true;
}

private void ApplyRotationAndScale(float offset)
{
    // Convert “offset” into angle and scale factor.
    float yawDegrees = -90f * offset;
    float scaleFactor = 1f + 0.2f * offset;

    Quaternion relativeRotation = Quaternion.AngleAxis(yawDegrees, Vector3.up);
    transform.localRotation = initialRotation * relativeRotation;
    transform.localScale = initialScale * scaleFactor;
}
