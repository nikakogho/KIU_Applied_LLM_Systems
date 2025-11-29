public override void ProcessInteractable(XRInteractionUpdateOrder.UpdatePhase updatePhase)
{
    if (updatePhase == XRInteractionUpdateOrder.UpdatePhase.Dynamic)
    {
        NativeArray<Color32> buffer = texture.GetRawTextureData<Color32>();
        Vector2 texSize = new Vector2(TextureSize, TextureSize);

        foreach (var interactor in interactorsSelecting)
        {
            // Compute the local touch position from the interactor's attach transform.
            Vector3 localTouch = transform.InverseTransformPoint(interactor.GetAttachTransform(this).position);

            // Convert to UV coordinates on the quad.
            Vector2 uv = new Vector2(localTouch.x + 0.5f, localTouch.y + 0.5f);
            Vector2 current = Vector2.Scale(texSize, uv);

            if (!lastPositions.TryGetValue(interactor, out Vector2 previous))
            {
                previous = current;
            }

            float length = Vector2.Distance(previous, current);
            for (int s = 0; s < length; s++)
            {
                float t = s / length;
                Vector2 pos = Vector2.Lerp(previous, current, t);
                DrawSplat(pos, buffer);
            }

            if (lastPositions.ContainsKey(interactor))
            {
                lastPositions[interactor] = current;
            }
            else
            {
                lastPositions.Add(interactor, current);
            }
        }

        texture.Apply(false);
    }
}
