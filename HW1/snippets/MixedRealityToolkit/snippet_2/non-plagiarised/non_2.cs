private bool _initialized;

/// <summary>
/// Slider callback that interprets movement as a normalized factor,
/// then uses that factor to rotate and scale the object.
/// </summary>
public void HandleSliderMovement(SliderEventData args)
{
    if (!_initialized)
    {
        initialRotation = transform.localRotation;
        initialScale = transform.localScale;
        initialSliderValue = args.NewValue;
        _initialized = true;
    }

    float offset = args.NewValue - initialSliderValue;

    // Treat offset in [-1, 1] as a normalized factor in [0, 1].
    float factor = Mathf.InverseLerp(-1f, 1f, offset);

    float yaw = Mathf.Lerp(0f, -90f, factor);
    float scaleFactor = Mathf.Lerp(1f, 1.2f, factor);

    Quaternion rotation = Quaternion.AngleAxis(yaw, Vector3.up);
    transform.localRotation = initialRotation * rotation;
    transform.localScale = initialScale * scaleFactor;
}
