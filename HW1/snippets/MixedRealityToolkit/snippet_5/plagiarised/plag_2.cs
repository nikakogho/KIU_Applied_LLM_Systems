public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    if (updatePhase != XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        return;
    }

    NativeArray<Color32> data = texture.GetRawTextureData<Color32>();
    Vector2 textureDimensions = new Vector2(TextureSize, TextureSize);

    foreach (var interactor in interactorsSelecting)
    {
        Transform attach = interactor.GetAttachTransform(this);
        Vector3 local = transform.InverseTransformPoint(attach.position);

        // Map local XY into UV space.
        Vector2 uv = new Vector2(local.x + 0.5f, local.y + 0.5f);
        Vector2 currentPixel = Vector2.Scale(textureDimensions, uv);

        // Default last position is the current position if we haven't seen this interactor yet.
        if (!lastPositions.TryGetValue(interactor, out Vector2 previousPixel))
        {
            previousPixel = currentPixel;
        }

        float dist = Vector2.Distance(previousPixel, currentPixel);
        if (dist > 0f)
        {
            for (int i = 0; i < dist; i++)
            {
                float alpha = i / dist;
                Vector2 p = Vector2.Lerp(previousPixel, currentPixel, alpha);
                DrawSplat(p, data);
            }
        }

        lastPositions[interactor] = currentPixel;
    }

    texture.Apply(false);
}
