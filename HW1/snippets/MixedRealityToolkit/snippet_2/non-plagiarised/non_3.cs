private bool _setupDone;
private float _startSliderValue;
private Quaternion _startRotation;
private Vector3 _startScale;

[SerializeField]
private float smoothing = 10f;

/// <summary>
/// Interprets slider input as a target pose and smoothly interpolates the object toward it.
/// Should be called regularly with the current slider value.
/// </summary>
public void UpdateFromSlider(SliderEventData args)
{
    if (!_setupDone)
    {
        _startSliderValue = args.NewValue;
        _startRotation = transform.localRotation;
        _startScale = transform.localScale;
        _setupDone = true;
    }

    float offset = args.NewValue - _startSliderValue;

    // Convert offset to direct target angle/scale.
    float targetAngle = -90f * offset;
    float targetScaleFactor = 1f + 0.2f * offset;

    Quaternion targetRotation = _startRotation * Quaternion.AngleAxis(targetAngle, Vector3.up);
    Vector3 targetScale = _startScale * targetScaleFactor;

    // Smoothly move towards the target instead of snapping.
    float t = 1f - Mathf.Exp(-smoothing * Time.deltaTime);
    transform.localRotation = Quaternion.Slerp(transform.localRotation, targetRotation, t);
    transform.localScale = Vector3.Lerp(transform.localScale, targetScale, t);
}
