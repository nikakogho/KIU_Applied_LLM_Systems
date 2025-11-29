public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    // Only react during the dynamic update phase.
    if (updatePhase != XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        return;
    }

    NativeArray<Color32> pixels = texture.GetRawTextureData<Color32>();

    foreach (var interactor in interactorsSelecting)
    {
        // World touch -> local space.
        var attachTransform = interactor.GetAttachTransform(this);
        Vector3 localPoint = transform.InverseTransformPoint(attachTransform.position);

        // Local [-0.5,0.5] -> UV [0,1].
        Vector2 uv = new Vector2(localPoint.x + 0.5f, localPoint.y + 0.5f);

        // UV -> pixel coords.
        Vector2 pixel = Vector2.Scale(new Vector2(TextureSize, TextureSize), uv);

        // Retrieve last position if we have seen this interactor.
        if (!lastPositions.TryGetValue(interactor, out Vector2 previousPixel))
        {
            previousPixel = pixel;
        }

        float distance = Vector2.Distance(previousPixel, pixel);

        // Draw splats along the segment from previousPixel to pixel.
        for (int step = 0; step < distance; step++)
        {
            float t = step / distance;
            Vector2 sample = Vector2.Lerp(previousPixel, pixel, t);
            DrawSplat(sample, pixels);
        }

        // Update dictionary with the new last position.
        lastPositions[interactor] = pixel;
    }

    texture.Apply(false);
}
