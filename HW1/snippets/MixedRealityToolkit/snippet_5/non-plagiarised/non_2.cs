public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    if (updatePhase != XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        return;
    }

    var pixels = texture.GetRawTextureData<Color32>();

    foreach (var interactor in interactorsSelecting)
    {
        Vector2 current = GetPixelCoordinate(interactor);
        Vector2 previous = current;

        if (lastPositions.TryGetValue(interactor, out var stored))
        {
            previous = stored;
        }

        DrawInterpolatedStroke(previous, current, pixels);
        lastPositions[interactor] = current;
    }

    texture.Apply(false);
}

private Vector2 GetPixelCoordinate(IXRSelectInteractor interactor)
{
    var attach = interactor.GetAttachTransform(this);
    var local = transform.InverseTransformPoint(attach.position);

    float u = Mathf.Clamp01(local.x + 0.5f);
    float v = Mathf.Clamp01(local.y + 0.5f);

    float px = u * TextureSize;
    float py = v * TextureSize;
    return new Vector2(px, py);
}

private void DrawInterpolatedStroke(Vector2 start, Vector2 end, NativeArray<Color32> data)
{
    float distance = Vector2.Distance(start, end);

    // Use a normalized parameter t in [0..1] with a step based on distance.
    float stepSize = 1f / Mathf.Max(1f, distance);
    for (float t = 0f; t <= 1f; t += stepSize)
    {
        Vector2 p = Vector2.Lerp(start, end, t);
        DrawSplat(p, data);
    }
}
