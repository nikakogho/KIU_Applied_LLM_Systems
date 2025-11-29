public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    if (updatePhase != XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        return;
    }

    var pixelData = texture.GetRawTextureData<Color32>();

    foreach (var interactor in interactorsSelecting)
    {
        Vector2 currentPixel = WorldToPixel(interactor);
        Vector2 lastPixel = GetLastPixelForInteractor(interactor, currentPixel);

        DrawLineBetween(lastPixel, currentPixel, pixelData);
        lastPositions[interactor] = currentPixel;
    }

    texture.Apply(false);
}

private Vector2 WorldToPixel(IXRSelectInteractor interactor)
{
    Transform attach = interactor.GetAttachTransform(this);
    Vector3 local = transform.InverseTransformPoint(attach.position);

    // Local [-0.5,0.5] -> UV [0,1]
    Vector2 uv = new Vector2(local.x + 0.5f, local.y + 0.5f);

    // UV -> pixel coordinates
    var texSize = new Vector2(TextureSize, TextureSize);
    return Vector2.Scale(texSize, uv);
}

private Vector2 GetLastPixelForInteractor(IXRSelectInteractor interactor, Vector2 fallback)
{
    if (lastPositions.TryGetValue(interactor, out var last))
    {
        return last;
    }

    return fallback;
}

private void DrawLineBetween(Vector2 from, Vector2 to, NativeArray<Color32> data)
{
    float distance = Vector2.Distance(from, to);
    int steps = Mathf.Max(1, Mathf.CeilToInt(distance));

    for (int i = 0; i <= steps; i++)
    {
        float t = i / (float)steps;
        Vector2 p = Vector2.Lerp(from, to, t);
        DrawSplat(p, data);
    }
}
