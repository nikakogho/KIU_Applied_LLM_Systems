public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    switch (updatePhase)
    {
        case XRInteractionUpdateOrder.UpdatePhase.Dynamic:
            HandleDynamicUpdate();
            break;
        // Other phases could be handled here if needed.
    }
}

private void HandleDynamicUpdate()
{
    var pixels = texture.GetRawTextureData<Color32>();

    foreach (var interactor in interactorsSelecting)
    {
        Vector2 currentPixel = ComputeTouchPixel(interactor);

        if (!lastPositions.TryGetValue(interactor, out var lastPixel))
        {
            lastPixel = currentPixel;
        }

        RenderStroke(lastPixel, currentPixel, pixels);
        lastPositions[interactor] = currentPixel;
    }

    texture.Apply(false);
}

private Vector2 ComputeTouchPixel(IXRSelectInteractor interactor)
{
    Transform attach = interactor.GetAttachTransform(this);
    Vector3 localTouch = transform.InverseTransformPoint(attach.position);

    Vector2 uv = new Vector2(localTouch.x + 0.5f, localTouch.y + 0.5f);
    Vector2 dimensions = new Vector2(TextureSize, TextureSize);
    return Vector2.Scale(dimensions, uv);
}

private void RenderStroke(Vector2 start, Vector2 end, NativeArray<Color32> pixels)
{
    float length = Vector2.Distance(start, end);
    if (length < Mathf.Epsilon)
    {
        DrawSplat(start, pixels);
        return;
    }

    int segments = Mathf.Max(1, Mathf.RoundToInt(length));
    for (int i = 0; i <= segments; i++)
    {
        float t = i / (float)segments;
        Vector2 pos = Vector2.Lerp(start, end, t);
        DrawSplat(pos, pixels);
    }
}
